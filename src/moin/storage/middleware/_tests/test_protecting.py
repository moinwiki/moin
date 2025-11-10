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
from moin.constants.keys import PARENTID
from moin.storage.middleware.protecting import ProtectedRevision, ProtectingMiddleware, AccessDenied
from moin.user import User

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
                dict(name=[item_name], acl=acl, contenttype="text/plain;charset=utf-8"),
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
            dict(name=[UNPROTECTED], acl="joe:write", contenttype="text/plain;charset=utf-8"),
            BytesIO(UNPROTECTED_CONTENT),
        )
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.store_revision(
                dict(name=[PROTECTED], acl="boss:write", contenttype="text/plain;charset=utf-8"),
                BytesIO(UNPROTECTED_CONTENT),
            )

    def test_write_create(self):
        # Now testing:
        item_name = "newitem"
        item = self.pmw[item_name]
        item.store_revision(dict(name=[item_name], contenttype="text/plain;charset=utf-8"), BytesIO(b"new content"))

    def test_overwrite_revision(self):
        revid_unprotected, revid_protected = self.make_items("joe:write,destroy", "boss:write,destroy")
        # Now testing:
        item = self.pmw[UNPROTECTED]
        item.store_revision(
            dict(
                name=[UNPROTECTED],
                acl="joe:write,destroy",
                contenttype="text/plain;charset=utf-8",
                revid=revid_unprotected,
            ),
            BytesIO(UNPROTECTED_CONTENT),
            overwrite=True,
        )
        item = self.pmw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.store_revision(
                dict(
                    name=[PROTECTED],
                    acl="boss:write,destroy",
                    contenttype="text/plain;charset=utf-8",
                    revid=revid_protected,
                ),
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
