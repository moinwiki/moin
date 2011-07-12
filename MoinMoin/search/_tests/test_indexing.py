# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.search.indexing Tests
"""


import py

import shutil, tempfile
from datetime import datetime

from whoosh.qparser import QueryParser

from MoinMoin import log
from MoinMoin.search.indexing import WhooshIndex

# Documents what will be added to index
docs = {
        u"Document One": [
                         {
                          "wikiname": u"Test",
                          "name": u"Document One",
                          "uuid": u"68054804bd7141609b7c441143adf83d",
                          "rev_no": 0,
                          "mtime":  datetime(2011, 6, 10, 2, 17, 5),
                          "content": u"Wi-Fi",
                          "contenttype": u"text/plain;charset=utf-8",
                          "tags": [u"Rest", u"in", u"peace"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another", u"Stuff"],
                          "acl": u"JoeDoe:read,write",
                          "language": u"en",
                          "userid": u"1307875904.23.55111",
                          "address": u"127.0.0.1",
                          "hostname": u"localhost",
                        },
                        {
                          "wikiname": u"Test",
                          "name": u"Document One",
                          "uuid": u"68054804bd7141609b7c441143adf83d",
                          "rev_no": 1,
                          "mtime":  datetime(2011, 6, 12, 2, 17, 5),
                          "content": u"Mo in Moin",
                          "contenttype": u"text/plain;charset=utf-8",
                          "tags": [u"first_tag", u"second_tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another", u"Stuff"],
                          "acl": u"JoeDoe:read,write",
                          "language": u"en",
                          "address": u"195.54.14.254",
                          "hostname": u"kb.csu.ru",
                        },
                       ],
        u"Document Two": [
                         {
                          "wikiname": u"Test",
                          "name": u"Document Two",
                          "uuid": u"12354804bd7141609b7c441143adf83d",
                          "rev_no": 0,
                          "mtime":  datetime(2011, 6, 10, 1, 17, 5),
                          "content": u"Hello document one",
                          "contenttype": u"text/plain;charset=utf-8",
                          "tags": [u"first_tag", u"tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another"],
                          "acl": u"User:-write",
                          "language": u"en",
                          "userid": u"1307875904.23.55111",
                          "address": u"123.213.132.231",
                         },
                         {
                          "wikiname": u"Test",
                          "name": u"Document Two",
                          "uuid": u"12354804bd7141609b7c441143adf83d",
                          "rev_no": 1,
                          "mtime":  datetime(2011, 6, 12, 2, 20, 5),
                          "content": u"Hello document two",
                          "contenttype": u"text/plain;charset=utf-8",
                          "tags": [u"tag", u"second_tag"],
                          "itemlinks": [u"Home", u"Find"],
                          "itemtransclusions": [u"Another"],
                          "acl": u"User:read,write,admin",
                          "language": u"en",
                          "address": u"123.213.132.231",
                         },
                        ]
       }

# (field_name, search_string, expected_result_count_for_latest, excpected_result_count_for_all)
queries = [
           (u"wikiname", u"Test", 2, 4),
           (u"name", u"Document", 2, 4),
           (u"uuid", u"68054804bd7141609b7c441143adf83d", 1, 2),
           (u"rev_no", u"1", 2, 2),
           (u"content", u"moin", 1, 1),
           (u"contenttype", u"text/plain", 2, 4),
           (u"tags", u"first_tag", 1, 2),
           (u"itemlinks", u"Home", 2, None),
           (u"itemtransclusions", u"Stuff", 1, None),
           (u"acl", u"JoeDoe:read", 1, None),
           (u"language", u"en", 2, 4),
           (u"userid", u"1307875904.23.55111", 0, 2),
           (u"address", u"127.0.0.1", 0, 1),
           (u"hostname", u"kb.csu.ru", 1, 1),
          ]


class TestWhooshIndex(object):

    queries = []

    def setup_method(self, method):
        """ indexing: create temporary directory with indexes """

        self.index_dir = tempfile.mkdtemp('', 'moin-')

    def teardown_method(self, method):
        """ indexing: delete temporary directory """

        shutil.rmtree(self.index_dir)

    def testIndexSchema(self):
        """
        indexing: create temporary directory with indexes, add documents from
        "docs" to indexes, and check results using "queries"
        """

        index_object = WhooshIndex(index_dir=self.index_dir)
        latest_revs_index = index_object.latest_revisions_index
        all_revs_index = index_object.all_revisions_index

        # Add docs to indexes
        with all_revs_index.writer() as all_revs_writer:
            for item_name, documents in docs.items():
                for document in documents:
                    with latest_revs_index.writer() as latest_revs_writer:
                        latest_revs_writer.update_document(**document)
                    all_revs_names = all_revs_index.schema.names()
                    all_revs_doc = dict([(key, value)
                                         for key, value in document.items()
                                         if key in all_revs_names])

                    all_revs_writer.add_document(**all_revs_doc)

       # Check that all docs were added successfully
        with latest_revs_index.searcher() as latest_revs_searcher:
            with all_revs_index.searcher() as all_revs_searcher:
                for field_name, query, latest_res_len, all_res_len in queries:
                    query = QueryParser(field_name, latest_revs_index.schema).parse(query)
                    assert len(latest_revs_searcher.search(query)) == latest_res_len
                    if field_name in all_revs_index.schema.names():
                        assert len(all_revs_searcher.search(query)) == all_res_len
