# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Manage whoosh indexes
"""

import os, datetime

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option
from whoosh.filedb.multiproc import MultiSegmentWriter
from whoosh.index import open_dir, create_in, exists_in
from whoosh.index import EmptyIndexError

from MoinMoin.search.indexing import WhooshIndex
from MoinMoin.config import MTIME, NAME, CONTENTTYPE
from MoinMoin.error import FatalError
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError
from MoinMoin.util.mime import Type
from MoinMoin.search.indexing import backend_to_index
from MoinMoin.storage.backends.indexing import convert_to_indexable

from MoinMoin import log
logging = log.getLogger(__name__)

# Information about index and schema for latest and all revisions
latest_indexname_schema = ("latest_revisions_index", "latest_revisions_schema")
all_indexname_schema = ("all_revisions_index", "all_revisions_schema")
both_indexnames_schemas = [latest_indexname_schema, all_indexname_schema]


class IndexOperations(Command):
    description = 'Build indexes'

    option_list = (
        Option('--for', required=True, dest='indexname', type=str, choices=("all-revs", "latest-revs", "both"),
            help='For what type of indexes we will use action'),
        Option('--action', required=True, dest='action', type=str, choices=("build", "update", "clean", "move", "show"),
            help="""
                  Action for given indexes:
                  build -- Build in index_dir_tmp
                  update -- Update in index_dir
                  clean -- Clean index_dir
                  move  -- Move index files from index_dir_tmp to index_dir
                  show -- Show index contents for the given index.
                 """
               ),
        Option('--procs', '-p', required=False, dest='procs', type=int, default=None,
            help='Number of processors the writer will use.'),
        Option('--limitmb', '-l', required=False, dest='limitmb', type=int, default=10,
            help='Maximum memory (in megabytes) each index-writer will use for the indexing pool.'),
                  )

    def run(self, indexname, action, procs, limitmb):

        def build_index(indexnames_schemas):
            """
            Building in app.cfg.index_dir_tmp
            """
            indexnames = [indexname for indexname, schema in indexnames_schemas]
            with MultiSegmentWriter(all_rev_index, procs, limitmb) as all_rev_writer:
                with MultiSegmentWriter(latest_rev_index, procs, limitmb) as latest_rev_writer:
                    for item in backend.iter_items_noindex():
                        try:
                            rev_no = None
                            if "all_revisions_index" in indexnames:
                                for rev_no in item.list_revisions():
                                    revision = item.get_revision(rev_no)
                                    rev_content = convert_to_indexable(revision)
                                    metadata = backend_to_index(revision, rev_no, all_rev_schema, rev_content, interwikiname)
                                    all_rev_writer.add_document(**metadata)
                            else:
                                revision = item.get_revision(-1)
                                rev_no = revision.revno
                                rev_content = convert_to_indexable(revision)
                        except NoSuchRevisionError: # item has no such revision
                            continue
                        # revision is now the latest revision of this item
                        if "latest_revisions_index" in indexnames and rev_no:
                            metadata = backend_to_index(revision, rev_no, latest_rev_schema, rev_content, interwikiname)
                            latest_rev_writer.add_document(**metadata)

        def update_index(indexnames_schemas):
            """
            Updating index in app.cfg.index_dir_tmp
            """

            indexnames = [indexname for indexname, schema in indexnames_schemas]
            create_documents = []
            delete_documents = []
            latest_documents = []
            for item in backend.iter_items_noindex():
                backend_rev_list = item.list_revisions()
                if not backend_rev_list: # If item hasn't revisions, skipping it
                    continue
                name = item.get_revision(-1)[NAME]
                index_rev_list = item_index_revs(all_rev_searcher, name)
                add_rev_nos = set(backend_rev_list) - set(index_rev_list)
                if add_rev_nos:
                    if "all_revisions_index" in indexnames:
                        create_documents.append((item, add_rev_nos))
                    if "latest_revisions_index" in indexnames:
                        latest_documents.append((item, max(add_rev_nos))) # Add latest revision
                remove_rev_nos = set(index_rev_list) - set(backend_rev_list)
                if remove_rev_nos:
                    if "all_revisions_index" in indexnames:
                        delete_documents.append((item, remove_rev_nos))

            if "latest_revisions_index" in indexnames and latest_documents:
                with latest_rev_index.writer() as latest_rev_writer:
                    for item, rev_no in latest_documents:
                        revision = item.get_revision(rev_no)
                        rev_content = convert_to_indexable(revision)
                        converted_rev = backend_to_index(revision, rev_no, latest_rev_schema, rev_content, interwikiname)
                        found = latest_rev_searcher.document(name_exact=item.name,
                                                             wikiname=interwikiname
                                                            )
                        if not found:
                            latest_rev_writer.add_document(**converted_rev)
                        # Checking that last revision is the latest
                        elif found["rev_no"] < converted_rev["rev_no"]:
                            doc_number = latest_rev_searcher.document_number(name_exact=item.name, wikiname=interwikiname)
                            latest_rev_writer.delete_document(doc_number)
                            latest_rev_writer.add_document(**converted_rev)

            if "all_revisions_index" in indexnames and delete_documents:
                with all_rev_index.writer() as all_rev_writer:
                    for item, rev_nos in delete_documents:
                        for rev_no in rev_nos:
                            doc_number = all_rev_searcher.document_number(rev_no=rev_no,
                                                                          exact_name=item.name,
                                                                          wikiname=interwikiname
                                                                         )
                            if doc_number:
                                all_rev_writer.delete_document(doc_number)

            if "all_revisions_index" in indexnames and create_documents:
                with all_rev_index.writer() as all_rev_writer:
                    for item, rev_nos in create_documents:
                        for rev_no in rev_nos:
                            revision = item.get_revision(rev_no)
                            rev_content = convert_to_indexable(revision)
                            converted_rev = backend_to_index(revision, rev_no, all_rev_schema, rev_content, interwikiname)
                            all_rev_writer.add_document(**converted_rev)

        def clean_index(indexnames_schemas):
            """
            Clean given index in app.cfg.index_dir
            """
            for indexname, schema in indexnames_schemas:
                index_object.create_index(index_dir=app.cfg.index_dir,
                                          indexname=indexname,
                                          schema=schema
                                         )

        def move_index(indexnames_schemas):
            """
            Move given indexes from index_dir_tmp to index_dir
            """
            clean_index(indexnames_schemas)
            for indexname, schema in indexnames_schemas:
                if not exists_in(app.cfg.index_dir_tmp, indexname=indexname):
                    raise FatalError(u"Can't find %s in %s" % (indexname, app.cfg.index_dir_tmp))
                for filename in all_rev_index.storage.list():
                    src_file = os.path.join(app.cfg.index_dir_tmp, filename)
                    dst_file = os.path.join(app.cfg.index_dir, filename)
                    if indexname in filename and os.path.exists(src_file):
                        os.rename(src_file, dst_file)

        def show_index(indexnames_schemas):
            """
            Print documents in given index to stdout
            """

            for indexname, schema in indexnames_schemas:
                try:
                    if indexname == "all_revisions_index":
                        ix = open_dir(app.cfg.index_dir, indexname="all_revisions_index")
                    elif indexname == "latest_revisions_index":
                        ix = open_dir(app.cfg.index_dir, indexname="latest_revisions_index")
                    print "*** Revisions in", indexname
                    with ix.searcher() as searcher:
                        for rev in searcher.all_stored_fields():
                            name = rev.pop("name", u"")
                            content = rev.pop("content", u"")
                            for field, value in [("name", name), ] + sorted(rev.items()) + [("content", content), ]:
                                print "%s: %s" % (field, repr(value)[:70])
                            print "\n"
                    ix.close()
                except (IOError, OSError, EmptyIndexError) as err:
                    raise FatalError("%s [Can not open %s index" % str(err), indexname)

        def item_index_revs(searcher, name):
            """
            Return list of found documents for given name using index searcher
            """

            revs_found = searcher.documents(name_exact=name, wikiname=interwikiname)
            return [rev["rev_no"] for rev in revs_found]

        def do_action(action, indexnames_schemas):
            if action == "build":
                build_index(indexnames_schemas)
            elif action == "update":
                update_index(indexnames_schemas)
            elif action == "clean":
                clean_index(indexnames_schemas)
            elif action == "move":
                move_index(indexnames_schemas)
            elif action == "show":
                show_index(indexnames_schemas)

        backend = flaskg.unprotected_storage = app.unprotected_storage
        index_object = WhooshIndex(index_dir=app.cfg.index_dir_tmp)
        interwikiname = app.cfg.interwikiname
        if os.path.samefile(app.cfg.index_dir_tmp, app.cfg.index_dir):
            raise FatalError(u"cfg.index_dir and cfg.index_dir_tmp must point to different directories.")

        latest_rev_index = index_object.latest_revisions_index
        all_rev_index = index_object.all_revisions_index

        latest_rev_schema = latest_rev_index.schema
        all_rev_schema = all_rev_index.schema

        latest_rev_searcher = latest_rev_index.searcher()
        all_rev_searcher = all_rev_index.searcher()

        if indexname == "both":
            do_action(action, both_indexnames_schemas)
        elif indexname == "all-revs":
            do_action(action, (all_indexname_schema, ))
        elif indexname == "latest-revs":
            do_action(action, (latest_indexname_schema, ))
