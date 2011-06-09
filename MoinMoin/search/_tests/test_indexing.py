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

class WhooshIndexBase(object):

    queries = []

    def setup_method(self, method):
        self.index_dir = tempfile.mkdtemp('', 'moin-')

    def teardown_method(self, method):
        shutil.rmtree(self.index_dir)

    def testIndexSchema(self):
        index_object = WhooshIndex(index_dir=self.index_dir)
        index = getattr(index_object, self.index_name)
        writer = index.writer()

        for document in self.documents:
            writer.add_document(**document)
        writer.commit()

        with index.searcher() as searcher:
            for field_name, query in self.queries:
                query = QueryParser(field_name, index.schema).parse(query)
                result = searcher.search(query)
                assert len(result) == 1


class TestLatestRevsSchema(WhooshIndexBase):

        index_name = "latest_revisions_index"
        documents = [
                     {
                      "item_name": u"Document One",
                      "uuid": u"68054804bd7141609b7c441143adf83d",
                      "rev_no": 10,
                      "datetime": datetime.utcnow(),
                      "content": u"Oh moin gott",
                      "mimetype": u"text/plain;charset=utf-8",
                      "tags": [u"first_tag", u"second_tag"],
                      "itemlinks": [u"Home", u"Find"],
                      "itemtransclusions": [u"Another", u"Stuff"],
                      "acl": u"JoeDoe:read,write",
                      "language": u"en",
                      "metadata": u"Other related stuff",
                     }
                    ]
        queries = [
                   (u"item_name", u"Document"),
                   (u"uuid", u"68054804bd7141609b7c441143adf83d"),
                   (u"rev_no", u"10"),
                   (u"content", u"moin"),
                   (u"mimetype", u"text/plain"),
                   (u"tags", u"first_tag"),
                   (u"itemlinks", u"Home"),
                   (u"itemtransclusions", u"Stuff"),
                   (u"acl", u"JoeDoe:read"),
                   (u"language", u"en"),
                   (u"metadata", u"Other"),
                  ]


class TestAllRevsSchema(WhooshIndexBase):

        index_name = "all_revisions_index"
        documents = [
                     {
                      "item_name": u"Document One",
                      "uuid": u"58054804bd7141609b7c441143adf83d",
                      "rev_no": 9,
                      "datetime": datetime.utcnow(),
                      "content": u"Wi-Fi",
                      "mimetype": u"text/plain;charset=utf-8",
                      "tags": [u"Rest", u"in", u"peace"],
                      "language": u"en",
                      "metadata": u"Other related stuff",
                     }
                    ]
        all_revs_queries = [
                            (u"item_name", u"Document"),
                            (u"uuid", u"58054804bd7141609b7c441143adf83d"),
                            (u"rev_no", u"9"),
                            (u"content", u"wi-fi"),
                            (u"mimetype", u"text/plain;charset=utf-8"),
                            (u"tags", u"Rest"),
                            (u"language", u"en"),
                            (u"metadata", u"Other"),
                           ]
