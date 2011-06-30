1# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Build indexes
"""

import os, shutil, datetime

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option
from whoosh.filedb.multiproc import MultiSegmentWriter
from whoosh.index import create_in, exists_in

from MoinMoin.search.indexing import WhooshIndex
from MoinMoin.config import MTIME, NAME
from MoinMoin.error import FatalError
from MoinMoin.script.maint.update_indexes import UpdateIndexes
from MoinMoin.storage.error import NoSuchItemError

# Information about index and schema for latest and all revisions
latest_indexname_schema = ("latest_revisions_index", "latest_revisions_schema")
all_indexname_schema = ("all_revisions_index", "all_revisions_schema")
both_indexnames_schemas = (latest_indexname_schema, all_indexname_schema)

class RebuildIndexes(Command):
    description = 'Build indexes'

    option_list = (
        Option('--for', required=True, dest='indexname', type=str, choices=("all-revs", "latest-revs", "both"), 
            help='For what type of indexes we will use action'),
        Option('--action', required=True, dest='action', type=str, choices=("build", "update", "clean", "move"), 
            help='Action for given indexes:\n\
                  build -- Build in index_dir_tmp\n\
                  update -- Update in index_dir\n\
                  clean -- Clean index_dir\n\
                  move  -- Move index files from index_dir to index_dir_tmp'
               ),
        Option('--procs', '-p', required=False, dest='procs', type=int, default=None,
            help='Number of processors the writer.'),
        Option('--limitmb', '-l', required=False, dest='limitmb', type=int, default=10,
            help='Maximum memory (in megabytes) each index-writer will use for the indexing pool.'),
                  )

    # We use 3 separated functions because want to avoid checks and increase speed
    def run(self, indexname, action, procs, limitmb):
        # Building in app.cfg.index_dir_tmp
        def build_index(indexnames_schemas, path, clean):
            if clean:
                clean_indexes(indexnames_schemas, path, clean)
            indexnames = [indexname for indexname, schema in indexnames_schemas]
            with all_rev_index.writer() as all_rev_writer:
                with latest_rev_index.writer() as latest_rev_writer:
                    for item in backend.iter_items_noindex():
                        for rev_no in item.list_revisions():
                            if "all_revisions_index" in indexnames:
                                revision = item.get_revision(rev_no)
                                metadata = dict([(str(key), value)
                                                 for key, value in revision.items()
                                                 if key in all_rev_field_names])
                                metadata[MTIME] = datetime.datetime.fromtimestamp(metadata[MTIME])
                                metadata["rev_no"] = rev_no
                                all_rev_writer.add_document(**metadata)
                        # revision is now the latest revision of this item
                        if "latest_revisions_index" in indexnames:
                            revision = item.get_revision(rev_no)
                            metadata = dict([(str(key), value)
                                              for key, value in revision.items()
                                              if key in latest_rev_field_names])
                            metadata[MTIME] = datetime.datetime.fromtimestamp(metadata[MTIME])
                            metadata["rev_no"] = rev_no
                            latest_rev_writer.add_document(**metadata)

        # Updating index in app.cfg.index_dir
        def update_index(indexnames_schemas):
            indexnames = [indexname for indexname, schema in indexnames_schemas]
            create_documents = []
            delete_documents = []
            latest_documents = []
            for item in backend.iter_items_noindex():
                name = item.get_revision(0)[NAME]
                index_rev_list = item_index_revs(all_rev_searcher, name)
                backend_rev_list = item.list_revisions()
                add_rev_nos = set(backend_rev_list) - set(index_rev_list)
                if add_rev_nos:
                    if "all_revisions_index" in indexnames:
                        create_documents.append((name, add_rev_nos))
                    if "latest_revisions_index" in indexnames:
                        latest_documents.append((name, max(add_rev_nos))) # Add latest revision 
                remove_rev_nos = set(index_rev_list) - set(backend_rev_list)
                if "all_revisions_index" in indexnames and remove_rev_nos:
                    delete_documents.append((name, remove_rev_nos))

            if latest_documents:
                with latest_rev_index.writer() as latest_rev_writer:
                    for name, rev_no in latest_documents:
                        try:
                            storage_rev = backend.get_item(name).get_revision(rev_no)
                            converted_rev = backend_to_index(storage_rev, rev_no, latest_rev_field_names)
                            found = latest_rev_searcher.document(name=name.lower())
                            if not found:
                                latest_rev_writer.add_document(**converted_rev)
                            # Checking what last revision is the latest
                            elif found["rev_no"] < converted_rev["rev_no"]:
                                doc_number = latest_rev_searcher.document_number(name=name.lower())
                                latest_rev_writer.delete_document(doc_number)
                                latest_rev_writer.add_document(**converted_rev)
                        except NoSuchItemError:
                            # Item has been trashed, removing all stuff
                            doc_number = latest_rev_searcher.document_number(name=name.lower())
                            if doc_number:
                                latest_rev_writer.delete_document(doc_number)

            if delete_documents:
                with all_rev_index.writer() as all_rev_writer:
                    for name, rev_nos in delete_documents:
                        # If document with this name wasn't found in indexes
                        # then we just ignore it
                        if not rev_nos:
                            continue
                        for rev_no in rev_nos:
                            doc_number = all_rev_searcher.document_number(rev_no=rev_no,
                                                                          name=name.lower()
                                                                         )
                            if doc_number:
                                all_rev_writer.delete_document(doc_number)

            if create_documents:
                with all_rev_index.writer() as all_rev_writer:
                    for name, rev_nos in create_documents:
                        try:
                            for rev_no in rev_nos:
                                    storage_rev = backend.get_item(name).get_revision(rev_no)
                                    converted_rev = backend_to_index(storage_rev, rev_no, all_rev_field_names)
                                    all_rev_writer.add_document(**converted_rev)
                        except NoSuchItemError:
                            # Item has been trashed, removing all stuff
                            rev_nos = item_index_revs(all_rev_searcher, name.lower())
                            for rev_no in rev_nos:
                                doc_number = all_rev_searcher.document_number(rev_no=rev_no,
                                                                              name=name.lower()
                                                                             )
                                if doc_number:
                                    all_rev_writer.delete_document(doc_number)

        def clean_index(indexnames_schemas, path):
            for indexname, schema in indexnames_schemas:
                index_object.create_index(indexdir=path,
                                          indexname=indexname,
                                          schema=schema
                                         )

        def item_index_revs(searcher, name):
            name = name.lower()
            revs_found = searcher.documents(name=name)
            return [rev["rev_no"] for rev in revs_found]

        # Convert fields from backend format to whoosh schema
        def backend_to_index(backend_rev, rev_no, schema_fields):
            metadata = dict([(str(key), value)
                              for key, value in backend_rev.items()
                              if key in schema_fields])
            metadata[MTIME] = datetime.datetime.fromtimestamp(metadata[MTIME])
            metadata["rev_no"] = rev_no
            return metadata

        def do_action(action, indexnames_schemas):
            if action == "build":
                build_index(indexnames_schemas, app.cfg.index_dir_tmp, clean=False)
            elif action == "update":
                update_index(indexnames_schemas)
            elif action == "clean":
                clean_index(indexnames_schemas, app.cfg.index_dir)
            elif action == "move":
                for indexname, schema in indexnames_schemas:
                    if not exists_in(app.cfg.index_dir_tmp, indexname=indexname):
                        raise FatalError(u"Can't find %s in %s" % (indexname, app.cfg.index_dir_tmp))
                    for filename in latest_rev_index.storage.list():
                        if indexname in filename:
                            try:
                                os.remove(os.path.join(app.cfg.index_dir, filename))
                            except:
                                pass
                            shutil.move(os.path.join(app.cfg.index_dir_tmp, filename), app.cfg.index_dir)

        backend = flaskg.unprotected_storage = app.unprotected_storage
        index_object = WhooshIndex(index_dir=app.cfg.index_dir_tmp)
        if os.path.samefile(app.cfg.index_dir_tmp, app.cfg.index_dir):
            raise FatalError(u"app.cfg.index_dir and app.cfg.tmp_index_dir are equal")

        latest_rev_index = index_object.latest_revisions_index
        all_rev_index = index_object.all_revisions_index

        latest_rev_field_names = latest_rev_index.schema.names()
        all_rev_field_names = all_rev_index.schema.names()

        latest_rev_searcher = latest_rev_index.searcher()
        all_rev_searcher = all_rev_index.searcher()

        if indexname == "both":
            do_action(action, both_indexnames_schemas)
        elif indexname == "all-revs":
            do_action(action, (all_indexname_schema,))
        elif indexname == "latest-revs":
            do_action(action, (latest_indexname_schema,))
