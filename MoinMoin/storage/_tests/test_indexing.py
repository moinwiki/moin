# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - indexing
"""

import py

from MoinMoin._tests import update_item, nuke_item
from MoinMoin._tests.wikiconfig import Config
from MoinMoin.storage.middleware.indexing import ItemIndex
from MoinMoin.config import NAME

# Revisions for tests
document_revs = [{"wikiname": u"Test",
                  "name": u"DocumentOne",
                  "uuid": u"68054804bd7141609b7c441143adf83d",
                  "rev_no": 0,
                  "mtime":  1172969203.1,
                  "content": u"Some not very long content line",
                  "contenttype": u"text/plain;charset=utf-8",
                  "tags": [u"Rest", u"in", u"peace"],
                  "itemlinks": [u"Home", u"Find"],
                  "itemtransclusions": [u"Another", u"Stuff"],
                  "language": u"en",
                  "address": u"127.0.0.1",
                  "hostname": u"localhost",
                 },
                 {"wikiname": u"Test",
                  "name": u"DocumentOne",
                  "uuid": u"68054804bd7141609b7c441143adf83d",
                  "rev_no": 1,
                  "mtime":  1172969203.9,
                  "content": u"This line should be much better, but it isn't",
                  "contenttype": u"text/plain;charset=utf-8",
                  "tags": [u"first_tag", u"second_tag"],
                  "itemlinks": [u"Home", u"Find"],
                  "itemtransclusions": [u"Another", u"Stuff"],
                  "language": u"en",
                  "address": u"127.0.0.1",
                  "hostname": u"localhost",
                 },
                ]

class TestIndexing(object):

    def setup_method(self, method):
        self.wikiconfig = Config()
        self.item_index = ItemIndex(self.wikiconfig, force_create=True)
        self.all_revs_ix = self.item_index.index_object.all_revisions_index
        self.latest_revs_ix = self.item_index.index_object.latest_revisions_index

    def teardown_method(self, method):
        self.item_index.remove_index()

    def test_create_item(self):
        """ Try to search for non-existent revision, add it to backend and then search again """
        revision = document_revs[0]
        with self.all_revs_ix.searcher() as searcher:
            found_document = searcher.document(name_exact=revision[NAME])
        assert found_document is None
        with self.latest_revs_ix.searcher() as searcher:
            found_document = searcher.document(name_exact=revision[NAME])
        assert found_document is None
        backend_rev = update_item(revision[NAME], revision["rev_no"],
                                  revision, revision["content"])
        with self.all_revs_ix.searcher() as searcher:
            found_document = searcher.document(name_exact=revision[NAME])
        assert found_document is not None and found_document[NAME] == revision[NAME]
        with self.latest_revs_ix.searcher() as searcher:
            found_document = searcher.document(name_exact=revision[NAME])
        assert found_document is not None and found_document[NAME] == revision[NAME]

    def test_create_rev(self):
        """ Create 2 item revisions and try to search for them in backend """
        revision1, revision2 = document_revs
        backend_rev = update_item(revision1[NAME], revision1["rev_no"], revision1, revision1["content"])
        backend_rev = update_item(revision2[NAME], revision2["rev_no"], revision2, revision2["content"])
        with self.all_revs_ix.searcher() as searcher:
            found_documents = list(searcher.documents(name_exact=revision1[NAME]))
        assert len(found_documents) == 2
        with self.latest_revs_ix.searcher() as searcher:
            found_documents = list(searcher.documents(name_exact=revision2[NAME]))
        assert len(found_documents) == 1 and found_documents[0]["rev_no"] == 1

    def test_destroy(self):
        """ Create & Destroy test for backend item """
        py.test.skip("Anonymous can't destroy stuff from backend, thus we leave this test for now")
        revision = document_revs[0]
        backend_rev = update_item(revision[NAME], revision["rev_no"], revision, revision["content"])
        with self.all_revs_ix.searcher() as searcher:
            found_documents = list(searcher.documents(name_exact=revision[NAME]))
            assert len(found_documents) == 1
            nuke_item(revision[NAME])
            found_document = searcher.document(name_exact=revision[NAME])
            assert found_document is None
