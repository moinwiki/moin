# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Up to date indexes
"""

import os
from datetime import datetime
from operator import itemgetter

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.config import MTIME, NAME
from MoinMoin.search.indexing import WhooshIndex
from MoinMoin.storage.error import NoSuchItemError

class UpdateIndexes(Command):
    description = 'Up to date indexes'

    option_list = (
        Option('--for', required=True, dest='indexname', type=str, choices=("all-revs", "latest-revs", "both"), 
            help='Update given index'),
                  )

    def run(self, indexname):
        # return list with item rev_nos
        def item_index_revs(searcher, name):
            name = name.lower()
            revs_found = searcher.documents(name=name)
            return [rev["rev_no"] for rev in revs_found]

        # Convert fields from backend format to whoosh schema
        def backend_to_index(backend_rev, rev_no, schema_fields):
            metadata = dict([(str(key), value)
                              for key, value in backend_rev.items()
                              if key in schema_fields])
            metadata[MTIME] = datetime.fromtimestamp(metadata[MTIME])
            metadata["rev_no"] = rev_no
            return metadata

        backend = flaskg.unprotected_storage = app.unprotected_storage
        index_object = WhooshIndex()

        latest_rev_index = index_object.latest_revisions_index
        all_rev_index = index_object.all_revisions_index

        latest_rev_field_names = latest_rev_index.schema.names()
        all_rev_field_names = all_rev_index.schema.names()

        latest_rev_searcher = latest_rev_index.searcher()
        all_rev_searcher = all_rev_index.searcher()
        create_documents = []
        delete_documents = []
        latest_documents = []
        for item in backend.iter_items_noindex():
            name = item.get_revision(0)[NAME]
            index_rev_list = item_index_revs(all_rev_searcher, name)
            backend_rev_list = item.list_revisions()
            add_rev_nos = set(backend_rev_list) - set(index_rev_list)
            if add_rev_nos:
                if indexname in ["both", "all-revs"]:
                    create_documents.append((name, add_rev_nos))
                if indexname in ["both", "latest-revs"]:
                    latest_documents.append((name, max(add_rev_nos))) # Add latest revision 
            remove_rev_nos = set(index_rev_list) - set(backend_rev_list)
            if remove_rev_nos and indexname in ["both", "all-revs"]:
                delete_documents.append((name, remove_rev_nos))

        if latest_documents and indexname in ["both", "latest-revs"]:
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

        if indexname in ["both", "all-revs"]:
            with all_rev_index.writer() as all_rev_writer:
                for name, rev_nos in delete_documents:
                    # If document with this name wasn't found in indexes
                    # then we just ignore it
                    if not rev_nos:
                        break
                    for rev_no in rev_nos:
                        doc_number = all_rev_searcher.document_number(rev_no=rev_no,
                                                                      name=name.lower()
                                                                     )
                        if doc_number:
                            all_rev_writer.delete_document(doc_number)
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
