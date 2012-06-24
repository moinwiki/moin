# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - indexing middleware tests
"""


from __future__ import absolute_import, division

from StringIO import StringIO
import hashlib

import pytest

from flask import g as flaskg

from MoinMoin.config import NAME, SIZE, ITEMID, REVID, DATAID, HASH_ALGORITHM, CONTENT, COMMENT, \
                            LATEST_REVS, ALL_REVS

from ..indexing import IndexingMiddleware

from MoinMoin.auth import GivenAuth
from MoinMoin._tests import wikiconfig
from MoinMoin.storage.backends.stores import MutableBackend
from MoinMoin.storage.stores.memory import BytesStore as MemoryBytesStore
from MoinMoin.storage.stores.memory import FileStore as MemoryFileStore
from MoinMoin.storage import create_simple_mapping
from MoinMoin.storage.middleware import routing


def dumper(indexer, idx_name):
    print "*** %s ***" % idx_name
    for kvs in indexer.dump(idx_name=idx_name):
        for k, v in kvs:
            print k, repr(v)[:70]
        print


class TestIndexingMiddleware(object):
    reinit_storage = True # cleanup after each test method

    def setup_method(self, method):
        self.imw = flaskg.unprotected_storage

    def teardown_method(self, method):
        pass

    def test_nonexisting_item(self):
        item = self.imw[u'foo']
        assert not item # does not exist

    def test_store_revision(self):
        item_name = u'foo'
        data = 'bar'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=item_name), StringIO(data))
        revid = rev.revid
        # check if we have the revision now:
        item = self.imw[item_name]
        assert item # does exist
        rev = item.get_revision(revid)
        assert rev.meta[NAME] == item_name
        assert rev.data.read() == data
        revids = [rev.revid for rev in item.iter_revs()]
        assert revids == [revid]

    def test_overwrite_revision(self):
        item_name = u'foo'
        data = 'bar'
        newdata = 'baz'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=item_name, comment=u'spam'), StringIO(data))
        revid = rev.revid
        # clear revision:
        item.store_revision(dict(name=item_name, revid=revid, comment=u'no spam'), StringIO(newdata), overwrite=True)
        # check if the revision was overwritten:
        item = self.imw[item_name]
        rev = item.get_revision(revid)
        assert rev.meta[NAME] == item_name
        assert rev.meta[COMMENT] == u'no spam'
        assert rev.data.read() == newdata
        revids = [rev.revid for rev in item.iter_revs()]
        assert len(revids) == 1 # we still have the revision, cleared
        assert revid in revids # it is still same revid

    def test_destroy_revision(self):
        item_name = u'foo'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=item_name, mtime=1),
                                  StringIO('bar'), trusted=True)
        revid0 = rev.revid
        rev = item.store_revision(dict(name=item_name, mtime=2),
                                  StringIO('baz'), trusted=True)
        revid1 = rev.revid
        rev = item.store_revision(dict(name=item_name, mtime=3),
                                  StringIO('...'), trusted=True)
        revid2 = rev.revid
        print "revids:", revid0, revid1, revid2
        # destroy a non-current revision:
        item.destroy_revision(revid0)
        # check if the revision was destroyed:
        item = self.imw[item_name]
        with pytest.raises(KeyError):
            item.get_revision(revid0)
        revids = [rev.revid for rev in item.iter_revs()]
        print "after destroy revid0", revids
        assert sorted(revids) == sorted([revid1, revid2])
        # destroy a current revision:
        item.destroy_revision(revid2)
        # check if the revision was destroyed:
        item = self.imw[item_name]
        with pytest.raises(KeyError):
            item.get_revision(revid2)
        revids = [rev.revid for rev in item.iter_revs()]
        print "after destroy revid2", revids
        assert sorted(revids) == sorted([revid1])
        # destroy the last revision left:
        item.destroy_revision(revid1)
        # check if the revision was destroyed:
        item = self.imw[item_name]
        with pytest.raises(KeyError):
            item.get_revision(revid1)
        revids = [rev.revid for rev in item.iter_revs()]
        print "after destroy revid1", revids
        assert sorted(revids) == sorted([])

    def test_destroy_item(self):
        revids = []
        item_name = u'foo'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=item_name, mtime=1),
                                  StringIO('bar'), trusted=True)
        revids.append(rev.revid)
        rev = item.store_revision(dict(name=item_name, mtime=2),
                                  StringIO('baz'), trusted=True)
        revids.append(rev.revid)
        # destroy item:
        item.destroy_all_revisions()
        # check if the item was destroyed:
        item = self.imw[item_name]
        assert not item # does not exist

    def test_all_revisions(self):
        item_name = u'foo'
        item = self.imw[item_name]
        item.store_revision(dict(name=item_name), StringIO('does not count, different name'))
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=item_name), StringIO('1st'))
        item.store_revision(dict(name=item_name), StringIO('2nd'))
        item = self.imw[item_name]
        revs = [rev.data.read() for rev in item.iter_revs()]
        assert len(revs) == 2
        assert set(revs) == set(['1st', '2nd'])

    def test_latest_revision(self):
        item_name = u'foo'
        item = self.imw[item_name]
        item.store_revision(dict(name=item_name), StringIO('does not count, different name'))
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=item_name), StringIO('1st'))
        expected_rev = item.store_revision(dict(name=item_name), StringIO('2nd'))
        revs = list(self.imw.documents(name=item_name))
        assert len(revs) == 1  # there is only 1 latest revision
        assert expected_rev.revid == revs[0].revid  # it is really the latest one

    def test_auto_meta(self):
        item_name = u'foo'
        data = 'bar'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=item_name), StringIO(data))
        print repr(rev.meta)
        assert rev.meta[NAME] == item_name
        assert rev.meta[SIZE] == len(data)
        assert rev.meta[HASH_ALGORITHM] == hashlib.new(HASH_ALGORITHM, data).hexdigest()
        assert ITEMID in rev.meta
        assert REVID in rev.meta
        assert DATAID in rev.meta

    def test_documents(self):
        item_name = u'foo'
        item = self.imw[item_name]
        rev1 = item.store_revision(dict(name=item_name), StringIO('x'))
        rev2 = item.store_revision(dict(name=item_name), StringIO('xx'))
        rev3 = item.store_revision(dict(name=item_name), StringIO('xxx'))
        rev = self.imw.document(idx_name=ALL_REVS, size=2)
        assert rev
        assert rev.revid == rev2.revid
        revs = list(self.imw.documents(idx_name=ALL_REVS, size=2))
        assert len(revs) == 1
        assert revs[0].revid == rev2.revid

    def test_index_rebuild(self):
        # first we index some stuff the slow "on-the-fly" way:
        expected_latest_revids = []
        item_name = u'foo'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=1),
                                StringIO('does not count, different name'), trusted=True)
        expected_latest_revids.append(r.revid)
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=item_name, mtime=1),
                            StringIO('1st'), trusted=True)
        r = item.store_revision(dict(name=item_name, mtime=2),
                                StringIO('2nd'), trusted=True)
        expected_latest_revids.append(r.revid)

        # now we remember the index contents built that way:
        expected_latest_revs = list(self.imw.documents())
        expected_all_revs = list(self.imw.documents(idx_name=ALL_REVS))

        print "*** all on-the-fly:"
        self.imw.dump(idx_name=ALL_REVS)
        print "*** latest on-the-fly:"
        self.imw.dump(idx_name=LATEST_REVS)

        # now kill the index and do a full rebuild
        self.imw.close()
        self.imw.destroy()
        self.imw.create()
        self.imw.rebuild()
        self.imw.open()

        # read the index contents built that way:
        all_revs = list(self.imw.documents(idx_name=ALL_REVS))
        latest_revs = list(self.imw.documents())
        latest_revids = [rev.revid for rev in latest_revs]

        print "*** all rebuilt:"
        self.imw.dump(idx_name=ALL_REVS)
        print "*** latest rebuilt:"
        self.imw.dump(idx_name=LATEST_REVS)

        # should be all the same, order does not matter:
        assert sorted(expected_all_revs) == sorted(all_revs)
        assert sorted(expected_latest_revs) == sorted(latest_revs)
        assert sorted(latest_revids) == sorted(expected_latest_revids)

    def test_index_update(self):
        # first we index some stuff the slow "on-the-fly" way:
        expected_all_revids = []
        expected_latest_revids = []
        missing_revids = []
        item_name = u'updated'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=1),
                                StringIO('updated 1st'), trusted=True)
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        item_name = u'destroyed'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=1),
                                StringIO('destroyed 1st'), trusted=True)
        destroy_revid = r.revid
        # we destroy this item below, so we don't add it to expected_all_revids
        # we destroy this item below, so we don't add it to expected_latest_revids
        item_name = u'stayssame'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=1),
                                StringIO('stayssame 1st'), trusted=True)
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        r = item.store_revision(dict(name=item_name, mtime=2),
                                StringIO('stayssame 2nd'), trusted=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)

        dumper(self.imw, ALL_REVS)
        dumper(self.imw, LATEST_REVS)

        # now build a fresh index at tmp location:
        self.imw.create(tmp=True)
        self.imw.rebuild(tmp=True)

        # while the fresh index still sits at the tmp location, we update and add some items.
        # this will not change the fresh index, but the old index we are still using.
        item_name = u'updated'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=2),
                                StringIO('updated 2nd'), trusted=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)
        missing_revids.append(r.revid)
        item_name = u'added'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, mtime=1),
                                StringIO('added 1st'), trusted=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)
        missing_revids.append(r.revid)
        item_name = u'destroyed'
        item = self.imw[item_name]
        item.destroy_revision(destroy_revid)

        # now switch to the not-quite-fresh-any-more index we have built:
        self.imw.close()
        self.imw.move_index()
        self.imw.open()

        dumper(self.imw, ALL_REVS)
        dumper(self.imw, LATEST_REVS)

        # read the index contents we have now:
        all_revids = [doc[REVID] for doc in self.imw._documents(idx_name=ALL_REVS)]
        latest_revids = [doc[REVID] for doc in self.imw._documents()]

        # this index is outdated:
        for missing_revid in missing_revids:
            assert missing_revid not in all_revids
            assert missing_revid not in latest_revids

        # update the index:
        self.imw.close()
        self.imw.update()
        self.imw.open()

        dumper(self.imw, ALL_REVS)
        dumper(self.imw, LATEST_REVS)

        # read the index contents we have now:
        all_revids = [doc[REVID] for doc in self.imw._documents(idx_name=ALL_REVS)]
        latest_revids = [doc[REVID] for doc in self.imw._documents()]

        # now it should have the previously missing rev and all should be as expected:
        for missing_revid in missing_revids:
            assert missing_revid in all_revids
            assert missing_revid in latest_revids
        assert sorted(all_revids) == sorted(expected_all_revids)
        assert sorted(latest_revids) == sorted(expected_latest_revids)

    def test_revision_contextmanager(self):
        # check if rev.data is closed after leaving the with-block
        item_name = u'foo'
        meta = dict(name=item_name)
        data = 'some test content'
        item = self.imw[item_name]
        data_file = StringIO(data)
        with item.store_revision(meta, data_file) as rev:
            assert rev.data.read() == data
            revid = rev.revid
        with pytest.raises(ValueError):
            rev.data.read()
        with item.get_revision(revid) as rev:
            assert rev.data.read() == data
        with pytest.raises(ValueError):
            rev.data.read()

    def test_indexed_content(self):
        # TODO: this is a very simple check that assumes that data is put 1:1
        # into index' CONTENT field.
        item_name = u'foo'
        meta = dict(name=item_name, contenttype=u'text/plain')
        data = 'some test content\n'
        item = self.imw[item_name]
        data_file = StringIO(data)
        with item.store_revision(meta, data_file) as rev:
            expected_revid = rev.revid
        doc = self.imw._document(content=u'test')
        assert doc is not None
        assert expected_revid == doc[REVID]
        assert unicode(data) == doc[CONTENT]

class TestProtectedIndexingMiddleware(object):
    reinit_storage = True # cleanup after each test method

    class Config(wikiconfig.Config):
        auth = [GivenAuth(user_name=u'joe', autocreate=True), ]

    def setup_method(self, method):
        self.imw = flaskg.storage

    def teardown_method(self, method):
        pass

    def test_documents(self):
        item_name = u'public'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, acl=u'joe:read'), StringIO('public content'))
        revid_public = r.revid
        revids = [rev.revid for rev in self.imw.documents()
                  if rev.meta[NAME] != u'joe'] # the user profile is a revision in the backend
        assert revids == [revid_public]

    def test_getitem(self):
        item_name = u'public'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=item_name, acl=u'joe:read'), StringIO('public content'))
        revid_public = r.revid
        # now testing:
        item_name = u'public'
        item = self.imw[item_name]
        r = item[revid_public]
        assert r.data.read() == 'public content'

    def test_perf_create_only(self):
        pytest.skip("usually we do no performance tests")
        # determine create revisions performance
        # for the memory backend we use, this is likely mostly building the indexes
        item_name = u'foo'
        item = self.imw[item_name]
        for i in xrange(100):
            item.store_revision(dict(name=item_name, acl=u'joe:create joe:read'), StringIO('some content'))

    def test_perf_create_read(self):
        pytest.skip("usually we do no performance tests")
        # determine create + read revisions performance
        # for the memory backend we use, this is likely mostly building the indexes and
        # doing index lookups name -> itemid, itemid -> revids list
        item_name = u'foo'
        item = self.imw[item_name]
        for i in xrange(100):
            item.store_revision(dict(name=item_name, acl=u'joe:create joe:read'), StringIO('rev number {0}'.format(i)))
        for r in item.iter_revs():
            #print r.meta
            #print r.data.read()
            pass

