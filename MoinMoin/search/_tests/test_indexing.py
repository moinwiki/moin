# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.search.indexing Tests
"""


import py

import shutil, tempfile
from datetime import datetime

from whoosh.qparser import QueryParser

from MoinMoin.search.indexing import WhooshIndex


docs = {
        u"Document One": [
                         {
                          "item_name": u"Document One",
                          "uuid": u"68054804bd7141609b7c441143adf83d",
                          "rev_no": 0,
                          "datetime":  datetime(2011, 6, 10, 2, 17, 5),
                          "content": u"Wi-Fi",
                          "mimetype": u"text/plain;charset=utf-8",
                          "tags": [u"Rest", u"in", u"peace"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another", u"Stuff"],
                          "acl": u"JoeDoe:read,write",
                          "language": u"en",
                        },
                        {
                          "item_name": u"Document One",
                          "uuid": u"68054804bd7141609b7c441143adf83d",
                          "rev_no": 1,
                          "datetime":  datetime(2011, 6, 12, 2, 17, 5),
                          "content": u"Mo in Moin",
                          "mimetype": u"text/plain;charset=utf-8",
                          "tags": [u"first_tag", u"second_tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another", u"Stuff"],
                          "acl": u"JoeDoe:read,write",
                          "language": u"en",
                        },
                       ],
        u"Document Two": [
                         {
                          "item_name": u"Document Two",
                          "uuid": u"12354804bd7141609b7c441143adf83d",
                          "rev_no": 0,
                          "datetime":  datetime(2011, 6, 10, 1, 17, 5),
                          "content": u"Hello document one",
                          "mimetype": u"text/plain;charset=utf-8",
                          "tags": [u"first_tag", u"tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another"],
                          "acl": u"User:-write",
                          "language": u"en",
                         },
                         {
                          "item_name": u"Document Two",
                          "uuid": u"12354804bd7141609b7c441143adf83d",
                          "rev_no": 1,
                          "datetime":  datetime(2011, 6, 12, 2, 20, 5),
                          "content": u"Hello document two",
                          "mimetype": u"text/plain;charset=utf-8",
                          "tags": [u"tag", u"second_tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another"],
                          "acl": u"User:read,write,admin",
                          "language": u"en",
                         },
                        ]
       }

queries = [
           (u"item_name", u"Document", 2, 4),
           (u"uuid", u"68054804bd7141609b7c441143adf83d", 1, 2),
           (u"rev_no", u"1", 2, 2),
           (u"content", u"moin", 1, 1),
           (u"mimetype", u"text/plain", 2, 4),
           (u"tags", u"first_tag", 1, 2),
           (u"itemlinks", u"Home", 2, None),
           (u"itemtransclusions", u"Stuff", 1, None),
           (u"acl", u"JoeDoe:read", 1, None),
           (u"language", u"en", 2, 4),
          ]


class TestWhooshIndex(object):

    queries = []

    def setup_method(self, method):
        self.index_dir = tempfile.mkdtemp('', 'moin-')

    def teardown_method(self, method):
        shutil.rmtree(self.index_dir)

    def testIndexSchema(self):
        index_object = WhooshIndex(index_dir=self.index_dir)
        latest_revs_index = index_object.latest_revisions_index
        all_revs_index = index_object.all_revisions_index

        with all_revs_index.writer() as all_revs_writer:
            for item_name, documents in docs.items():
                for document in documents:
                    with latest_revs_index.writer() as latest_revs_writer:
                        latest_revs_writer.update_document(**document)
                    all_revs_names = all_revs_index.schema.names()
                    all_revs_doc = dict([(key, value)
                                         for key, value in document.items()
                                         if key in all_revs_names])

                    for document_field, value in document.items(): # Extract fields for all revs schema
                        for schema_field in all_revs_index.schema.names(): # is there way to rewrite this block shortly?
                            all_revs_doc[schema_field] = document[schema_field]

                    all_revs_writer.add_document(**all_revs_doc)

        with latest_revs_index.searcher() as latest_revs_searcher, all_revs_index.searcher() as all_revs_searcher:
            for field_name, query, latst_res_len, all_res_len in queries:
                query = QueryParser(field_name, latest_revs_index.schema).parse(query)
                assert len(latest_revs_searcher.search(query)) == latst_res_len
                if field_name in all_revs_index.schema.names():
                    assert len(all_revs_searcher.search(query)) == all_res_len
