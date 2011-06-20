# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Up to date indexes
"""

import os
from datetime import datetime

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option
from whoosh.index import create_in

from MoinMoin.search.indexing import WhooshIndex


class UpdateIndexes(Command):
    description = 'Up to date indexes'

    def run(self):
        backend = flaskg.unprotected_storage = app.unprotected_storage
        index_object = WhooshIndex()

        latest_rev_index = index_object.latest_revisions_index
        all_rev_index = index_object.all_revisions_index

        latest_rev_field_names = latest_rev_index.schema.names()
        all_rev_field_names = all_rev_index.schema.names()

        latest_rev_searcher = latest_rev_index.searcher()
        all_rev_searcher = all_rev_index.searcher()
        update_latest = []
        update_all = []
        # First step: delete old documents from latest and all indexes by internal doc id
        with all_rev_index.writer() as all_rev_writer:
            with latest_rev_index.writer() as latest_rev_writer:
                for item in backend.iter_items_noindex():
                    for rev_no in item.list_revisions():
                        revision = item.get_revision(rev_no)
                        metadata = dict([(str(key), value)
                                         for key, value in revision.items()
                                         if key in all_rev_field_names])
                        metadata["rev_no"] = rev_no
                        backend_mtime = metadata["mtime"] = datetime.fromtimestamp(metadata["mtime"])
                        doc_fields = all_rev_searcher.document(rev_no=metadata["rev_no"],
                                                               uuid=metadata["uuid"])
                        if doc_fields: # if we found document in indexes
                            index_mtime = doc_fields["mtime"]
                            if backend_mtime != index_mtime: # document has changed since last index update
                                # We'll delete document by internat id, and then
                                # add new document to update list
                                doc_number = all_rev_searcher.document_number(rev_no=metadata["rev_no"],
                                                                              uuid=metadata["uuid"])
                                all_rev_writer.delete_document(doc_number)
                                update_all.append(metadata)
                        else: # If document not found then add it to update list
                            update_all.append(metadata)
                    # same for latest revision
                    if doc_fields:
                        index_mtime = doc_fields["mtime"]
                        if backend_mtime != index_mtime: # document has changed since last index update
                            doc_number = latest_rev_searcher.document_number(rev_no=metadata["rev_no"],
                                                                          uuid=metadata["uuid"])
                            latest_rev_writer.delete_document(doc_number)
                            update_latest.append(metadata)
                    else:
                        update_latest.append(metadata)
        # Now updating indexes with new documents from update lists
        with latest_rev_index.writer() as latest_rev_writer:
            for doc in update_latest:
                latest_rev_writer.add_document(**doc)

        with all_rev_index.writer() as all_rev_writer:
            for doc in update_all:
                all_rev_writer.add_document(**doc)
