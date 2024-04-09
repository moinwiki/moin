# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - indexing middleware tests
"""

from io import BytesIO
import hashlib

from whoosh.query import Term
import pytest

from flask import g as flaskg

from moin.constants.keys import (
    NAME,
    NAME_EXACT,
    SIZE,
    ITEMID,
    REVID,
    DATAID,
    HASH_ALGORITHM,
    CONTENT,
    COMMENT,
    LATEST_REVS,
    ALL_REVS,
    NAMESPACE,
    NAMERE,
    NAMEPREFIX,
    CONTENTTYPE,
    ITEMTYPE,
    ITEMLINKS,
    REV_NUMBER,
    PARENTID,
    MTIME,
)

from moin.constants.namespaces import NAMESPACE_USERS

from moin.utils.interwiki import split_fqname

from moin.auth import GivenAuth
from moin._tests import wikiconfig, update_item


def dumper(indexer, idx_name):
    print("*** %s ***" % idx_name)
    for kvs in indexer.dump(idx_name=idx_name):
        for k, v in kvs:
            print(k, repr(v)[:70])
        print()


class TestIndexingMiddleware:
    reinit_storage = True  # cleanup after each test method

    @pytest.fixture(autouse=True)
    def imw(self):
        self.imw = flaskg.unprotected_storage
        return self.imw

    def test_nonexisting_item(self):
        item = self.imw["foo"]
        assert not item  # does not exist

    def test_store_revision(self):
        item_name = "foo"
        data = b"bar"
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name]), BytesIO(data), return_rev=True)
        revid = rev.revid
        # check if we have the revision now:
        item = self.imw[item_name]
        assert item  # does exist
        rev = item.get_revision(revid)
        assert rev.name == item_name
        assert rev.data.read() == data
        revids = [_rev.revid for _rev in item.iter_revs()]
        assert revids == [revid]

    def test_overwrite_revision(self):
        item_name = "foo"
        data = b"bar"
        newdata = b"baz"
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name], comment="spam"), BytesIO(data), return_rev=True)
        revid = rev.revid
        # clear revision:
        item.store_revision(dict(name=[item_name], revid=revid, comment="no spam"), BytesIO(newdata), overwrite=True)
        # check if the revision was overwritten:
        item = self.imw[item_name]
        rev = item.get_revision(revid)
        assert rev.name == item_name
        assert rev.meta[COMMENT] == "no spam"
        assert rev.data.read() == newdata
        revids = [_rev.revid for _rev in item.iter_revs()]
        assert len(revids) == 1  # we still have the revision, cleared
        assert revid in revids  # it is still same revid

    def _store_three_revs(self, acl=None):
        item_name = "foo"
        item = self.imw[item_name]
        rev = item.store_revision(
            dict(name=[item_name], mtime=1, acl=acl), BytesIO(b"bar"), trusted=True, return_rev=True
        )
        revid0 = rev.revid
        rev = item.store_revision(
            dict(name=[item_name], mtime=2, parentid=revid0, acl=acl), BytesIO(b"baz"), trusted=True, return_rev=True
        )
        revid1 = rev.revid
        rev = item.store_revision(
            dict(name=[item_name], mtime=3, parentid=revid1, acl=acl), BytesIO(b"..."), trusted=True, return_rev=True
        )
        revid2 = rev.revid
        print("revids:", revid0, revid1, revid2)
        return item, item_name, revid0, revid1, revid2

    def test_destroy_revision(self):
        item, item_name, revid0, revid1, revid2 = self._store_three_revs()
        query = Term(NAME_EXACT, item_name)
        metas = {m[REVID]: m for m in flaskg.storage.search_meta(query, idx_name=ALL_REVS)}
        rev1_mtime = metas[revid1][MTIME]
        # destroy a non-current revision:
        item.destroy_revision(revid0)
        # check if the revision was destroyed:
        metas = {m[REVID]: m for m in flaskg.storage.search_meta(query, idx_name=ALL_REVS)}
        revids = list(metas.keys())
        print("after destroy revid0", revids)
        assert sorted(revids) == sorted([revid1, revid2])
        # validate parent id of remaining revision is updated
        assert PARENTID not in metas[revid1]
        # validate mtime not updated
        assert rev1_mtime == metas[revid1][MTIME]
        # validate revid2 is still the current one
        metas = {m[REVID]: m for m in flaskg.storage.search_meta(query)}
        assert 1 == len(metas)
        assert revid2 in metas
        # destroy a current revision:
        item = self.imw[item_name]
        item.destroy_revision(revid2)
        # check if the revision was destroyed:
        item = self.imw[item_name]
        query = Term(NAME_EXACT, item_name)
        metas = flaskg.storage.search_meta(query, idx_name=ALL_REVS)
        revids = [meta[REVID] for meta in metas]
        print("after destroy revid2", revids)
        assert sorted(revids) == sorted([revid1])
        # destroy the last revision left:
        item.destroy_revision(revid1)
        # check if the revision was destroyed:
        item = self.imw[item_name]
        query = Term(NAME_EXACT, item_name)
        metas = flaskg.storage.search_meta(query, idx_name=ALL_REVS)
        revids = [meta[REVID] for meta in metas]
        print("after destroy revid1", revids)
        assert sorted(revids) == sorted([])

    def test_destroy_middle_revision(self):
        item, item_name, revid0, revid1, revid2 = self._store_three_revs()
        # destroy the middle revision:
        item.destroy_revision(revid1)
        with item.get_revision(revid2) as rev:
            # validate that the parentid of remaining rev was updated
            assert rev.meta[PARENTID] == revid0

    def test_destroy_item(self):
        revids = []
        item_name = "foo"
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name], mtime=1), BytesIO(b"bar"), trusted=True, return_rev=True)
        revids.append(rev.revid)
        rev = item.store_revision(dict(name=[item_name], mtime=2), BytesIO(b"baz"), trusted=True, return_rev=True)
        revids.append(rev.revid)
        # destroy item:
        item.destroy_all_revisions()
        # check if the item was destroyed:
        item = self.imw[item_name]
        assert not item  # does not exist

    def test_all_revisions(self):
        item_name = "foo"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name]), BytesIO(b"does not count, different name"))
        item_name = "bar"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name]), BytesIO(b"1st"))
        item.store_revision(dict(name=[item_name]), BytesIO(b"2nd"))
        item = self.imw[item_name]
        revs = [rev.data.read() for rev in item.iter_revs()]
        assert len(revs) == 2
        assert set(revs) == {b"1st", b"2nd"}

    def test_latest_revision(self):
        item_name = "foo"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name]), BytesIO(b"does not count, different name"))
        item_name = "bar"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name]), BytesIO(b"1st"))
        expected_rev = item.store_revision(dict(name=[item_name]), BytesIO(b"2nd"), return_rev=True)
        revs = list(self.imw.documents(name=item_name))
        assert len(revs) == 1  # there is only 1 latest revision
        assert expected_rev.revid == revs[0].revid  # it is really the latest one

    def test_auto_meta(self):
        item_name = "foo"
        data = b"bar"
        item = self.imw[item_name]
        rev = item.store_revision(dict(name=[item_name]), BytesIO(data), return_rev=True)
        print(repr(rev.meta))
        assert rev.name == item_name
        assert rev.meta[SIZE] == len(data)
        assert rev.meta[HASH_ALGORITHM] == hashlib.new(HASH_ALGORITHM, data).hexdigest()
        assert ITEMID in rev.meta
        assert REVID in rev.meta
        assert DATAID in rev.meta

    def test_meta_itemlinks_moin(self):
        meta1 = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ITEMTYPE: "default", REV_NUMBER: 1}
        rev1 = update_item("item01", meta1, "[[Home]] [[users/user]] [[/Subitem01]]")
        assert "Home" in rev1.meta[ITEMLINKS]
        assert "users/user" in rev1.meta[ITEMLINKS]
        assert "item01/Subitem01" in rev1.meta[ITEMLINKS]
        meta2 = {
            CONTENTTYPE: "text/x.moin.wiki;charset=utf-8",
            NAME: ["user"],
            NAMESPACE: NAMESPACE_USERS,
            ITEMTYPE: "default",
            REV_NUMBER: 1,
        }
        rev2 = update_item("%s/user" % NAMESPACE_USERS, meta2, "[[users/usr1]] [[../usr2]]")
        assert "users/usr1" in rev2.meta[ITEMLINKS]
        assert "users/usr2" in rev2.meta[ITEMLINKS]

    def test_documents(self):
        item_name = "foo"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name]), BytesIO(b"x"), return_rev=True)
        rev2 = item.store_revision(dict(name=[item_name]), BytesIO(b"xx"), return_rev=True)
        item.store_revision(dict(name=[item_name]), BytesIO(b"xxx"), return_rev=True)
        rev = self.imw.document(idx_name=ALL_REVS, size=2)
        assert rev
        assert rev.revid == rev2.revid
        revs = list(self.imw.documents(idx_name=ALL_REVS, size=2))
        assert len(revs) == 1
        assert revs[0].revid == rev2.revid

    def test_xml_document(self):
        """Test that XML documents can be stored and indexed."""
        item_name = "foo"
        item = self.imw[item_name]
        meta = dict(name=[item_name], contenttype="text/xml")
        rev = item.store_revision(meta, BytesIO(b'<?xml version="1.0" encoding="UTF-8"?>'), return_rev=True)
        assert rev

    def test_index_rebuild(self):
        # first we index some stuff the slow "on-the-fly" way:
        expected_latest_revids = []
        item_name = "foo"
        item = self.imw[item_name]
        r = item.store_revision(
            dict(name=[item_name], mtime=1), BytesIO(b"does not count, different name"), trusted=True, return_rev=True
        )
        expected_latest_revids.append(r.revid)
        item_name = "bar"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name], mtime=2), BytesIO(b"1st"), trusted=True)
        r = item.store_revision(dict(name=[item_name], mtime=3), BytesIO(b"2nd"), trusted=True, return_rev=True)
        expected_latest_revids.append(r.revid)

        # now we remember the index contents built that way:
        expected_latest_revs = list(self.imw.documents())
        expected_all_revs = list(self.imw.documents(idx_name=ALL_REVS))

        print("*** all on-the-fly:")
        self.imw.dump(idx_name=ALL_REVS)
        print("*** latest on-the-fly:")
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

        print("*** all rebuilt:")
        self.imw.dump(idx_name=ALL_REVS)
        print("*** latest rebuilt:")
        self.imw.dump(idx_name=LATEST_REVS)

        # should be all the same, order does not matter:
        print(len(expected_all_revs), sorted(expected_all_revs))
        print(len(all_revs), sorted(all_revs))
        assert sorted(expected_all_revs) == sorted(all_revs)
        assert sorted(expected_latest_revs) == sorted(latest_revs)
        assert sorted(latest_revids) == sorted(expected_latest_revids)

    def test_index_update(self):
        # first we index some stuff the slow "on-the-fly" way:
        expected_all_revids = []
        expected_latest_revids = []
        missing_revids = []
        item_name = "updated"
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name], mtime=1), BytesIO(b"updated 1st"), trusted=True, return_rev=True)
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        item_name = "destroyed"
        item = self.imw[item_name]
        r = item.store_revision(
            dict(name=[item_name], mtime=1), BytesIO(b"destroyed 1st"), trusted=True, return_rev=True
        )
        destroy_revid = r.revid
        # we destroy this item below, so we don't add it to expected_all_revids
        # we destroy this item below, so we don't add it to expected_latest_revids
        item_name = "stayssame"
        item = self.imw[item_name]
        r = item.store_revision(
            dict(name=[item_name], mtime=1), BytesIO(b"stayssame 1st"), trusted=True, return_rev=True
        )
        expected_all_revids.append(r.revid)
        # we update this item below, so we don't add it to expected_latest_revids
        r = item.store_revision(
            dict(name=[item_name], mtime=2), BytesIO(b"stayssame 2nd"), trusted=True, return_rev=True
        )
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)

        dumper(self.imw, ALL_REVS)
        dumper(self.imw, LATEST_REVS)

        # now build a fresh index at tmp location:
        self.imw.create(tmp=True)
        self.imw.rebuild(tmp=True)

        # while the fresh index still sits at the tmp location, we update and add some items.
        # this will not change the fresh index, but the old index we are still using.
        item_name = "updated"
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name], mtime=2), BytesIO(b"updated 2nd"), trusted=True, return_rev=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)
        missing_revids.append(r.revid)
        item_name = "added"
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name], mtime=1), BytesIO(b"added 1st"), trusted=True, return_rev=True)
        expected_all_revids.append(r.revid)
        expected_latest_revids.append(r.revid)
        missing_revids.append(r.revid)
        item_name = "destroyed"
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
        item_name = "foo"
        meta = dict(name=[item_name])
        data = b"some test content"
        item = self.imw[item_name]
        data_file = BytesIO(data)
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
        item_name = "foo"
        meta = dict(name=[item_name], contenttype="text/plain;charset=utf-8")
        data = b"some test content\n"
        item = self.imw[item_name]
        data_file = BytesIO(data)
        with item.store_revision(meta, data_file, return_rev=True) as rev:
            expected_revid = rev.revid
        doc = self.imw._document(content="test")
        assert doc is not None
        assert expected_revid == doc[REVID]
        assert doc[CONTENT] == data.decode()

    def test_indexing_subscriptions(self):
        item_name = "foo"
        meta = dict(name=[item_name], subscriptions=[f"{NAME}::foo", f"{NAMERE}::.*"])
        item = self.imw[item_name]
        item.store_revision(meta, BytesIO(item_name.encode("utf-8")))
        doc1 = self.imw.document(subscription_ids=f"{NAME}::foo")
        doc2 = self.imw.document(subscription_patterns=f"{NAMERE}::.*")
        assert doc1 is not None
        assert doc2 is not None
        doc3 = self.imw.document(subscription_ids=f"{NAMERE}::.*")
        doc4 = self.imw.document(subscription_patterns=f"{NAMEPREFIX}::foo")
        assert doc3 is None
        assert doc4 is None

    def test_namespaces(self):
        item_name_n = "normal"
        item = self.imw[item_name_n]
        rev_n = item.store_revision(
            dict(name=[item_name_n], contenttype="text/plain;charset=utf-8"),
            BytesIO(item_name_n.encode("utf-8")),
            return_rev=True,
        )
        item_name_u = "%s/user" % NAMESPACE_USERS
        fqname_u = split_fqname(item_name_u)
        item = self.imw.get_item(**fqname_u.query)
        rev_u = item.store_revision(
            dict(name=[fqname_u.value], namespace=fqname_u.namespace, contenttype="text/plain;charset=utf-8"),
            BytesIO(item_name_u.encode("utf-8")),
            return_rev=True,
        )
        item = self.imw[item_name_n]
        rev_n = item.get_revision(rev_n.revid)
        assert rev_n.meta[NAMESPACE] == ""
        assert rev_n.meta[NAME] == [item_name_n]
        item = self.imw[item_name_u]
        rev_u = item.get_revision(rev_u.revid)
        assert rev_u.meta[NAMESPACE] == NAMESPACE_USERS
        assert rev_u.meta[NAME] == [item_name_u.split("/")[1]]

    def test_parentnames(self):
        item_name = "child"
        item = self.imw[item_name]
        item.store_revision(
            dict(name=["child", "p1/a", "p2/b", "p2/c", "p3/p4/d"], contenttype="text/plain;charset=utf-8"),
            BytesIO(b""),
        )
        item = self.imw[item_name]
        assert item.parentnames == {"p1", "p2", "p3/p4"}  # one p2 duplicate removed


class TestProtectedIndexingMiddleware:
    reinit_storage = True  # cleanup after each test method

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            auth = [GivenAuth(user_name="joe", autocreate=True)]

        return Config

    @pytest.fixture(autouse=True)
    def imw(self):
        self.imw = flaskg.unprotected_storage

    def test_documents(self):
        item_name = "public"
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name], acl="joe:read"), BytesIO(b"public content"), return_rev=True)
        revid_public = r.revid
        revids = [
            rev.revid for rev in self.imw.documents() if rev.name != "joe"
        ]  # the user profile is a revision in the backend
        assert revids == [revid_public]

    def test_getitem(self):
        item_name = "public"
        item = self.imw[item_name]
        r = item.store_revision(dict(name=[item_name], acl="joe:read"), BytesIO(b"public content"), return_rev=True)
        revid_public = r.revid
        # now testing:
        item_name = "public"
        item = self.imw[item_name]
        r = item[revid_public]
        assert r.data.read() == b"public content"

    def test_perf_create_only(self):
        pytest.skip("usually we do no performance tests")
        # determine create revisions performance
        # for the memory backend we use, this is likely mostly building the indexes
        item_name = "foo"
        item = self.imw[item_name]
        for i in range(100):
            item.store_revision(dict(name=[item_name], acl="joe:create joe:read"), BytesIO(b"some content"))

    def test_perf_create_read(self):
        pytest.skip("usually we do no performance tests")
        # determine create + read revisions performance
        # for the memory backend we use, this is likely mostly building the indexes and
        # doing index lookups name -> itemid, itemid -> revids list
        item_name = "foo"
        item = self.imw[item_name]
        for i in range(100):
            item.store_revision(dict(name=[item_name], acl="joe:create joe:read"), BytesIO(b"rev number {}".format(i)))
        for r in item.iter_revs():
            # print r.meta
            # print r.data.read()
            pass
