# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - protecting middleware tests.
"""

from __future__ import annotations

import pytest

from io import BytesIO
from typing import TYPE_CHECKING

from moin.config import AclConfig
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.constants.keys import (
    ACL,
    ALL_REVS,
    CONTENTTYPE,
    LATEST_REVS,
    MTIME,
    NAME,
    NAME_EXACT,
    ITEMTYPE,
    PARENTID,
    REVID,
)
from moin.storage.middleware.exceptions import AccessDenied
from moin.storage.middleware.protecting import ProtectedRevision, ProtectingMiddleware
from moin.user import User
from whoosh.query import Or, Term

from .test_indexing import TestIndexingMiddlewareBase

UNPROTECTED = "unprotected"
PROTECTED = "protected"

UNPROTECTED_CONTENT = b"unprotected content"
PROTECTED_CONTENT = b"protected content"

acl_mapping = [
    ("", AclConfig(before="", default="joe:read,write,create,admin All:read,write,create", after="", hierarchic=False)),
    (
        "users",
        AclConfig(before="", default="joe:read,write,create,admin All:read,write,create", after="", hierarchic=False),
    ),
]


class FakeUser(User):
    """
    Fake user object; provides user.name.
    """

    def __init__(self, name):
        self.name = [name]

    @property
    def name0(self):
        return self.name[0]


@pytest.mark.usefixtures("_req_ctx", "_imw", "_protected_imw")
class TestProtectingMiddleware(TestIndexingMiddlewareBase):

    if TYPE_CHECKING:

        def __init__(self):
            self.pmw: ProtectingMiddleware

    @pytest.fixture
    def _protected_imw(self) -> None:
        self.pmw = ProtectingMiddleware(self.imw, FakeUser("joe"), acl_mapping=acl_mapping)

    def make_items(self, unprotected_acl: str, protected_acl: str):
        items = [(UNPROTECTED, unprotected_acl, UNPROTECTED_CONTENT), (PROTECTED, protected_acl, PROTECTED_CONTENT)]
        revids = []
        for item_name, acl, content in items:
            item = self.pmw[item_name]
            r = item.store_revision(
                {NAME: [item_name], ITEMTYPE: ITEMTYPE_DEFAULT, ACL: acl, CONTENTTYPE: "text/plain;charset=utf-8"},
                BytesIO(content),
                return_rev=True,
            )
            assert r is not None
            assert isinstance(r, ProtectedRevision)
            revids.append(r.revid)
        return revids

    def test_documents(self):
        revid_unprotected, revid_protected = self.make_items("joe:read", "boss:read")
        revids = [rev.revid for rev in self.pmw.documents()]
        assert revids == [revid_unprotected]  # without revid_protected!

    def test_search_acl_contract_unreadable_never_surfaced(self):
        # Contract: no search method may surface an unreadable item, on either
        # index. Any future search path added without a read filter fails here.
        revid_unprotected, revid_protected = self.make_items("joe:read", "boss:read")
        query = Or([Term(NAME_EXACT, UNPROTECTED), Term(NAME_EXACT, PROTECTED)])
        for idx_name in (LATEST_REVS, ALL_REVS):
            assert [rev.revid for rev in self.pmw.search(query, idx_name=idx_name)] == [revid_unprotected]
            assert [rev.revid for rev in self.pmw.search_page(query, idx_name=idx_name)] == [revid_unprotected]
            assert [meta[REVID] for meta in self.pmw.search_meta(query, idx_name=idx_name)] == [revid_unprotected]
            assert [
                meta[REVID]
                for meta in self.pmw.search_meta_page(query, idx_name=idx_name, sortedby=[MTIME], pagenum=1, pagelen=10)
            ] == [revid_unprotected]
            assert [rev.revid for rev in self.pmw.documents(idx_name=idx_name)] == [revid_unprotected]
            assert self.pmw.search_results_size(query, idx_name=idx_name) == 1

    def test_search_results_size_counts_past_whoosh_default_limit(self):
        # whoosh caps a search at limit=10 by default; the count must not
        # be capped: all 12 items are readable, so lifting it keeps all 12.
        names = [f"bulk{i:02d}" for i in range(12)]
        for name in names:
            item = self.pmw[name]
            r = item.store_revision(
                {NAME: [name], ITEMTYPE: ITEMTYPE_DEFAULT, ACL: "joe:read", CONTENTTYPE: "text/plain;charset=utf-8"},
                BytesIO(b"bulk"),
                return_rev=True,
            )
            assert r is not None
            assert isinstance(r, ProtectedRevision)
        query = Or([Term(NAME_EXACT, name) for name in names])
        assert self.pmw.search_results_size(query, idx_name=ALL_REVS) == len(names)
        # all 12 are readable: with the whoosh limit lifted the filter keeps all
        assert len(list(self.pmw.search_meta(query, idx_name=ALL_REVS, limit=None))) == len(names)

    def test_getitem(self):
        revid_unprotected, revid_protected = self.make_items("joe:read", "boss:read")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        r = item[revid_unprotected]
        assert r.data.read() == UNPROTECTED_CONTENT
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            r = item[revid_protected]

    def test_write(self):
        revid_unprotected, revid_protected = self.make_items("joe:write", "boss:write")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        item.store_revision(
            {
                NAME: [UNPROTECTED],
                ITEMTYPE: ITEMTYPE_DEFAULT,
                ACL: "joe:write",
                CONTENTTYPE: "text/plain;charset=utf-8",
            },
            BytesIO(UNPROTECTED_CONTENT),
        )
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.store_revision(
                {
                    NAME: [PROTECTED],
                    ITEMTYPE: ITEMTYPE_DEFAULT,
                    ACL: "boss:write",
                    CONTENTTYPE: "text/plain;charset=utf-8",
                },
                BytesIO(UNPROTECTED_CONTENT),
            )

    def test_write_create(self):
        # Now testing:
        item_name = "newitem"
        item = self.pmw[item_name]
        item.store_revision(
            {NAME: [item_name], ITEMTYPE: ITEMTYPE_DEFAULT, CONTENTTYPE: "text/plain;charset=utf-8"},
            BytesIO(b"new content"),
        )

    def test_overwrite_revision(self):
        revid_unprotected, revid_protected = self.make_items("joe:write,destroy", "boss:write,destroy")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        item.store_revision(
            {
                NAME: [UNPROTECTED],
                ITEMTYPE: ITEMTYPE_DEFAULT,
                ACL: "joe:write,destroy",
                CONTENTTYPE: "text/plain;charset=utf-8",
                REVID: revid_unprotected,
            },
            BytesIO(UNPROTECTED_CONTENT),
            overwrite=True,
        )
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.store_revision(
                {
                    NAME: [PROTECTED],
                    ITEMTYPE: ITEMTYPE_DEFAULT,
                    ACL: "boss:write,destroy",
                    CONTENTTYPE: "text/plain;charset=utf-8",
                    REVID: revid_protected,
                },
                BytesIO(UNPROTECTED_CONTENT),
                overwrite=True,
            )

    def test_destroy_revision(self):
        revid_unprotected, revid_protected = self.make_items("joe:destroy", "boss:destroy")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        item.destroy_revision(revid_unprotected)
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.destroy_revision(revid_protected)

    def test_destroy_middle_revision(self):
        item, item_name, revid0, revid1, revid2 = self.store_three_revisions("joe:read,write,destroy")
        # Destroy the middle revision:
        item.destroy_revision(revid1)
        with item.get_revision(revid2) as rev:
            # Validate that the parentid of the remaining revision was updated
            assert rev.meta[PARENTID] == revid0

    def test_destroy_item(self):
        revid_unprotected, revid_protected = self.make_items("joe:destroy", "boss:destroy")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        item.destroy_all_revisions()
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.destroy_all_revisions()
