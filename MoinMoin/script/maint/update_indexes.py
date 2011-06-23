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
from whoosh.index import create_in

from MoinMoin.config import MTIME, UUID, NAME
from MoinMoin.search.indexing import WhooshIndex


class UpdateIndexes(Command):
    description = 'Up to date indexes'


    def run(self):
        # yield dict with fields of each revision by given uuid
        def yield_index_rev(searcher, name):
            name = name.lower()
            sorted_list = sorted(searcher.documents(name=name), key=itemgetter('rev_no'), reverse=True)
            if not sorted_list: # if doc with this uuid doesn't exist
                yield None
            for revision in sorted_list:
                yield revision

        # Iterate over backend item revisions
        def yield_backend_rev(item):
            for revision in reversed(item.list_revisions()):
                yield {revision: item.get_revision(revision)}

        # Convert fields from backend fortat to whoosh schema
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
        add_list = []
        latest_add_list = []
        with all_rev_index.writer() as all_rev_writer:
            with latest_rev_index.writer() as latest_rev_writer:
                for item in backend.iter_items_noindex(): 
                    name = item.get_revision(0)[NAME]
                    index_rev_iter = yield_index_rev(all_rev_searcher, name)
                    backend_rev_iter = yield_backend_rev(item)

                    index_rev = index_rev_iter.next()
                    backend_rev = backend_rev_iter.next()

                    latest_rev_doc = latest_rev_searcher.document(name=name)
                    for rev_no, rev_metadata in backend_rev.items(): # dict contains only 1 revision
                        converted_rev = backend_to_index(backend_rev=rev_metadata,
                                                         rev_no=rev_no,
                                                         schema_fields=latest_rev_field_names
                                                        )
                    # Checking updates for last revision in latest revision indexes
                    if not latest_rev_doc:
                        latest_add_list.append(converted_rev)
                    elif converted_rev["rev_no"] != latest_rev_doc["rev_no"]:
                        latest_add_list.append(converted_rev)
                        doc_number = latest_rev_searcher.document_number(rev_no=latest_index_rev[u"rev_no"],
                                                                         name=name
                                                                        )
                        latest_rev_writer.delete_document(doc_number)
                    # Converting revision to all_revs_schema
                    for rev_no, rev_metadata in backend_rev.items(): # dict contains only 1 revision
                        converted_rev = backend_to_index(backend_rev=rev_metadata,
                                                         rev_no=rev_no,
                                                         schema_fields=all_rev_field_names
                                                        )
                    while True:
                        try:
                            # if document with this uuid not found in indexes
                            print "CONVERTED:", converted_rev
                            print "INDEX:", index_rev
                            if not index_rev:
                                # Add all revisions from backend to add_list
                                print "tango"
                                for backend_rev in yield_backend_rev(item):
                                    for rev_no, rev_metadata in backend_rev.items(): # dict contains only 1 revision
                                        converted_rev = backend_to_index(backend_rev=rev_metadata,
                                                                         rev_no=rev_no,
                                                                         schema_fields=all_rev_field_names
                                                                        )
                                        add_list.append(converted_rev)
                                break
                            # Documents are equal, then take another
                            if converted_rev["rev_no"] == index_rev["rev_no"]:
                                print "ecko"
                                index_rev = index_rev_iter.next()
                                backend_rev = backend_rev_iter.next()
                                for rev_no, rev_metadata in backend_rev.items():
                                    converted_rev = backend_to_index(backend_rev=rev_metadata,
                                                                     rev_no=rev_no,
                                                                     schema_fields=all_rev_field_names
                                                                    )
                            # Backend's document rev doesn't exist in index
                            if converted_rev["rev_no"] > index_rev["rev_no"]:
                                print "charlie"
                                add_list.append(converted_rev)
                                backend_rev = backend_rev_iter.next()
                                for rev_no, rev_metadata in backend_rev.items():
                                    converted_rev = backend_to_index(backend_rev=rev_metadata,
                                                                     rev_no=rev_no,
                                                                     schema_fields=all_rev_field_names
                                                                    )
                            # Index's document rev doesn't exist in backend
                            if converted_rev["rev_no"] < index_rev["rev_no"]:
                                print "bravo"
                                print "REVISION", index_rev[u"rev_no"], "NAME", index_rev[NAME]
                                index_name = index_rev[NAME].lower()
                                doc_number = all_rev_searcher.document_number(rev_no=index_rev[u"rev_no"],
                                                                              name=index_name
                                                                             )
                                print doc_number
                                all_rev_writer.delete_document(doc_number) # I think that could be done with delete_by_term()
                                index_rev = index_rev_iter.next()
                        except StopIteration:
                            # We reached the end
                            break
        # Second step: add revisions from add lists to indexes
        with latest_rev_index.writer() as latest_rev_writer:
            # update latest revisions
            for rev in latest_add_list:
                latest_rev_writer.add_document(**rev)

        with all_rev_index.writer() as all_rev_writer:
        # update all revisions
            print "***Documents what will be added to all index"
            for rev in add_list:
                print rev
                all_rev_writer.add_document(**rev)
