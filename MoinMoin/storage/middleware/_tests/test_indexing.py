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

from MoinMoin.constants.keys import (NAME, SIZE, ITEMID, REVID, DATAID, HASH_ALGORITHM, CONTENT, COMMENT,
                                     LATEST_REVS, ALL_REVS, NAMESPACE, NAMERE, NAMEPREFIX)
from MoinMoin.constants.namespaces import NAMESPACE_USERPROFILES

from MoinMoin.util.interwiki import split_fqname

from MoinMoin.auth import GivenAuth
from MoinMoin._tests import wikiconfig


def dumper(indexer, idx_name):
    print "*** %s ***" % idx_name
    for kvs in indexer.dump(idx_name=idx_name):
        for k, v in kvs:
            print k, repr(v)[:70]
        print


class TestIndexingMiddleware(object):
    reinit_storage = True  # cleanup after each test method

    def setup_method(self, method):
        self.imw = flaskg.unprotected_storage

    def teardown_method(self, method):
        pass

    def test_nonexisting_item(self):
        item = self.imw[u'foo']
        assert not item  # does not exist

    def test_store_revision(self):
        item_name = u'foo'
        data = 'bar'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name, ]), StringIO(data),
                                  return_rev=True)
        revid = rev.revid
        # check if we have the revision now:
        item = self.imw[item_name]
        assert item  # does exist
        rev = item.get_revision(revid)
        assert rev.name == item_name
        assert rev.data.read() == data
        revids = [rev.revid for rev in item.iter_revs()]
        assert revids == [revid]

    def test_overwrite_revision(self):
        item_name = u'foo'
        data = 'bar'
        newdata = 'baz'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name, ], comment=u'spam'), StringIO(data),
                                  return_rev=True)
        revid = rev.revid
        # clear revision:
        item.store_revision(dict(name=[item_name, ], revid=revid, comment=u'no spam'), StringIO(newdata), overwrite=True)
        # check if the revision was overwritten:
        item = self.imw[item_name]
        rev = item.get_revision(revid)
        assert rev.name == item_name
        assert rev.meta[COMMENT] == u'no spam'
        assert rev.data.read() == newdata
        revids = [rev.revid for rev in item.iter_revs()]
        assert len(revids) == 1  # we still have the revision, cleared
        assert revid in revids  # it is still same revid

    def test_destroy_revision(self):
        item_name = u'foo'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name, ], mtime=1),
                                  StringIO('bar'), trusted=True, return_rev=True)
        revid0 = rev.revid
        rev = item.store_revision(dict(name=[item_name, ], mtime=2),
                                  StringIO('baz'), trusted=True, return_rev=True)
        revid1 = rev.revid
        rev = item.store_revision(dict(name=[item_name, ], mtime=3),
                                  StringIO('...'), trusted=True, return_rev=True)
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
        rev = item.store_revision(dict(name=[item_name, ], mtime=1),
                                  StringIO('bar'), trusted=True, return_rev=True)
        revids.append(rev.revid)
        rev = item.store_revision(dict(name=[item_name, ], mtime=2),
                                  StringIO('baz'), trusted=True, return_rev=True)
        revids.append(rev.revid)
        # destroy item:
        item.destroy_all_revisions()
        # check if the item was destroyed:
        item = self.imw[item_name]
        assert not item  # does not exist

    def test_all_revisions(self):
        item_name = u'foo'
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name, ]), StringIO('does not count, different name'))
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name, ]), StringIO('1st'))
        item.store_revision(dict(name=[item_name, ]), StringIO('2nd'))
        item = self.imw[item_name]
        revs = [rev.data.read() for rev in item.iter_revs()]
        assert len(revs) == 2
        assert set(revs) == set(['1st', '2nd'])

    def test_latest_revision(self):
        item_name = u'foo'
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name, ]), StringIO('does not count, different name'))
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name, ]), StringIO('1st'))
        expected_rev = item.store_revision(dict(name=[item_name, ]), StringIO('2nd'),
                                           return_rev=True)
        revs = list(self.imw.documents(name=item_name))
        assert len(revs) == 1  # there is only 1 latest revision
        assert expected_rev.revid == revs[0].revid  # it is really the latest one

    def test_auto_meta(self):
        item_name = u'foo'
        data = 'bar'
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name, ]), StringIO(data), return_rev=True)
        print repr(rev.meta)
        assert rev.name == item_name
        assert rev.meta[SIZE] == len(data)
        assert rev.meta[HASH_ALGORITHM] == hashlib.new(HASH_ALGORITHM, data).hexdigest()
        assert ITEMID in rev.meta
        assert REVID in rev.meta
        assert DATAID in rev.meta

    def test_documents(self):
        item_name = u'foo'
        item = self.imw[item_name]
        rev1 = item.store_revision(dict(name=[item_name, ]), StringIO('x'), return_rev=True)
        rev2 = item.store_revision(dict(name=[item_name, ]), StringIO('xx'), return_rev=True)
        rev3 = item.store_revision(dict(name=[item_name, ]), StringIO('xxx'), return_rev=True)
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
        r = item.store_revision(dict(name=[item_name, ], mtime=1),
                                StringIO('does not count, different name'),
                                trusted=True, return_rev=True)
        expected_latest_revids.append(r.revid)
        item_name = u'bar'
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name, ], mtime=1),
                            StringIO('1st'), trusted=True)
        r = item.store_revision(dict(name=[item_name, ], mtime=2),
                                StringIO('2nd'), trusted=True, return_rev=True)
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
        r = item.store_revision(dict(name=[item_name, ], mtime=1),
                                StringIO('updated 1st'),
                                trusted=True, return_rev=True)
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        item_name = u'destroyed'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name, ], mtime=1),
                                StringIO('destroyed 1st'),
                                trusted=True, return_rev=True)
        destroy_revid = r.revid
        # we destroy this item below, so we don't add it to expected_all_revids
        # we destroy this item below, so we don't add it to expected_latest_revids
        item_name = u'stayssame'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name, ], mtime=1),
                                StringIO('stayssame 1st'),
                                trusted=True, return_rev=True)
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        r = item.store_revision(dict(name=[item_name, ], mtime=2),
                                StringIO('stayssame 2nd'),
                                trusted=True, return_rev=True)
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
        r = item.store_revision(dict(name=[item_name, ], mtime=2),
                                StringIO('updated 2nd'), trusted=True,
                                return_rev=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)
        missing_revids.append(r.revid)
        item_name = u'added'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name, ], mtime=1),
                                StringIO('added 1st'),
                                trusted=True, return_rev=True)
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
        meta = dict(name=[item_name, ])
        data = 'some test content'
        item = self.imw[item_name]
        data_file = StringIO(data)
        with item.store_revision(meta, data_file, return_rev=True) as rev:
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
        meta = dict(name=[item_name, ], contenttype=u'text/plain;charset=utf-8')
        data = 'some test content\n'
        item = self.imw[item_name]
        data_file = StringIO(data)
        with item.store_revision(meta, data_file, return_rev=True) as rev:
            expected_revid = rev.revid
        doc = self.imw._document(content=u'test')
        assert doc is not None
        assert expected_revid == doc[REVID]
        assert unicode(data) == doc[CONTENT]

    def test_indexing_subscriptions(self):
        item_name = u"foo"
        meta = dict(name=[item_name, ], subscriptions=[u"{0}::foo".format(NAME),
                                                       u"{0}::.*".format(NAMERE)])
        item = self.imw[item_name]
        item.store_revision(meta, StringIO(str(item_name)))
        doc1 = self.imw.document(subscription_ids=u"{0}::foo".format(NAME))
        doc2 = self.imw.document(subscription_patterns=u"{0}::.*".format(NAMERE))
        assert doc1 is not None
        assert doc2 is not None
        doc3 = self.imw.document(subscription_ids=u"{0}::.*".format(NAMERE))
        doc4 = self.imw.document(subscription_patterns=u"{0}::foo".format(NAMEPREFIX))
        assert doc3 is None
        assert doc4 is None

    def test_namespaces(self):
        item_name_n = u'normal'
        item = self.imw[item_name_n]
        rev_n = item.store_revision(dict(name=[item_name_n, ], contenttype=u'text/plain;charset=utf-8'),
                                    StringIO(str(item_name_n)), return_rev=True)
        item_name_u = u'%s/userprofile' % NAMESPACE_USERPROFILES
        fqname_u = split_fqname(item_name_u)
        item = self.imw.get_item(**fqname_u.query)
        rev_u = item.store_revision(dict(name=[fqname_u.value], namespace=fqname_u.namespace, contenttype=u'text/plain;charset=utf-8'),
                                    StringIO(str(item_name_u)), return_rev=True)
        item = self.imw[item_name_n]
        rev_n = item.get_revision(rev_n.revid)
        assert rev_n.meta[NAMESPACE] == u''
        assert rev_n.meta[NAME] == [item_name_n, ]
        item = self.imw[item_name_u]
        rev_u = item.get_revision(rev_u.revid)
        assert rev_u.meta[NAMESPACE] == NAMESPACE_USERPROFILES
        assert rev_u.meta[NAME] == [item_name_u.split('/')[1]]

    def test_parentnames(self):
        item_name = u'child'
        item = self.imw[item_name]
        item.store_revision(dict(name=[u'child', u'p1/a', u'p2/b', u'p2/c', u'p3/p4/d', ],
                                 contenttype=u'text/plain;charset=utf-8'),
                            StringIO(''))
        item = self.imw[item_name]
        assert item.parentnames == [u'p1', u'p2', u'p3/p4', ]  # one p2 duplicate removed


class TestProtectedIndexingMiddleware(object):
    reinit_storage = True  # cleanup after each test method

    class Config(wikiconfig.Config):
        auth = [GivenAuth(user_name=u'joe', autocreate=True), ]

    def setup_method(self, method):
        self.imw = flaskg.storage

    def teardown_method(self, method):
        pass

    def test_documents(self):
        item_name = u'public'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name, ], acl=u'joe:read'),
                                StringIO('public content'), return_rev=True)
        revid_public = r.revid
        revids = [rev.revid for rev in self.imw.documents()
                  if rev.name != u'joe']  # the user profile is a revision in the backend
        assert revids == [revid_public]

    def test_getitem(self):
        item_name = u'public'
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name, ], acl=u'joe:read'),
                                StringIO('public content'), return_rev=True)
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
            item.store_revision(dict(name=[item_name, ], acl=u'joe:create joe:read'), StringIO('some content'))

    def test_perf_create_read(self):
        pytest.skip("usually we do no performance tests")
        # determine create + read revisions performance
        # for the memory backend we use, this is likely mostly building the indexes and
        # doing index lookups name -> itemid, itemid -> revids list
        item_name = u'foo'
        item = self.imw[item_name]
        for i in xrange(100):
            item.store_revision(dict(name=[item_name, ], acl=u'joe:create joe:read'), StringIO('rev number {0}'.format(i)))
        for r in item.iter_revs():
            # print r.meta
            # print r.data.read()
            pass
