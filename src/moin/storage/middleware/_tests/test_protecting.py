# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - protecting middleware tests
"""

from io import BytesIO

import pytest

from moin.constants.keys import PARENTID

from ..protecting import ProtectingMiddleware, AccessDenied

from .test_indexing import TestIndexingMiddleware

UNPROTECTED = "unprotected"
PROTECTED = "protected"

UNPROTECTED_CONTENT = b"unprotected content"
PROTECTED_CONTENT = b"protected content"

acl_mapping = [
    ("", dict(before="", default="joe:read,write,create,admin All:read,write,create", after="", hierarchic=False)),
    ("users", dict(before="", default="joe:read,write,create,admin All:read,write,create", after="", hierarchic=False)),
]


class FakeUser:
    """
    fake user object, just to give user.name
    """

    def __init__(self, name):
        self.name = [name]

    @property
    def name0(self):
        return self.name[0]


class TestProtectingMiddleware(TestIndexingMiddleware):
    @pytest.fixture(autouse=True)
    def protected_imw(self, imw):
        self.imw = ProtectingMiddleware(imw, FakeUser("joe"), acl_mapping=acl_mapping)
        return self.imw

    def _dummy(self):
        # replacement for tests that use unsupported methods / attributes
        pass

    test_index_rebuild = _dummy
    test_index_update = _dummy
    test_indexed_content = _dummy

    def make_items(self, unprotected_acl, protected_acl):
        items = [(UNPROTECTED, unprotected_acl, UNPROTECTED_CONTENT), (PROTECTED, protected_acl, PROTECTED_CONTENT)]
        revids = []
        for item_name, acl, content in items:
            item = self.imw[item_name]
            r = item.store_revision(
                dict(name=[item_name], acl=acl, contenttype="text/plain;charset=utf-8"),
                BytesIO(content),
                return_rev=True,
            )
            revids.append(r.revid)
        return revids

    def test_documents(self):
        revid_unprotected, revid_protected = self.make_items("joe:read", "boss:read")
        revids = [rev.revid for rev in self.imw.documents()]
        assert revids == [revid_unprotected]  # without revid_protected!

    def test_getitem(self):
        revid_unprotected, revid_protected = self.make_items("joe:read", "boss:read")
        # now testing:
        item = self.imw[UNPROTECTED]
        r = item[revid_unprotected]
        assert r.data.read() == UNPROTECTED_CONTENT
        item = self.imw[PROTECTED]
        with pytest.raises(AccessDenied):
            r = item[revid_protected]

    def test_write(self):
        revid_unprotected, revid_protected = self.make_items("joe:write", "boss:write")
        # now testing:
        item = self.imw[UNPROTECTED]
        item.store_revision(
            dict(name=[UNPROTECTED], acl="joe:write", contenttype="text/plain;charset=utf-8"),
            BytesIO(UNPROTECTED_CONTENT),
        )
        item = self.imw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.store_revision(
                dict(name=[PROTECTED], acl="boss:write", contenttype="text/plain;charset=utf-8"),
                BytesIO(UNPROTECTED_CONTENT),
            )

    def test_write_create(self):
        # now testing:
        item_name = "newitem"
        item = self.imw[item_name]
        item.store_revision(dict(name=[item_name], contenttype="text/plain;charset=utf-8"), BytesIO(b"new content"))

    def test_overwrite_revision(self):
        revid_unprotected, revid_protected = self.make_items("joe:write,destroy", "boss:write,destroy")
        # now testing:
        item = self.imw[UNPROTECTED]
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
        item = self.imw[PROTECTED]
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
        # now testing:
        item = self.imw[UNPROTECTED]
        item.destroy_revision(revid_unprotected)
        item = self.imw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.destroy_revision(revid_protected)

    def test_destroy_middle_revision(self):
        item, item_name, revid0, revid1, revid2 = self._store_three_revs("joe:read,write,destroy")
        # destroy the middle revision:
        item.destroy_revision(revid1)
        with item.get_revision(revid2) as rev:
            # validate that the parentid of remaining rev was updated
            assert rev.meta[PARENTID] == revid0

    def test_destroy_item(self):
        revid_unprotected, revid_protected = self.make_items("joe:destroy", "boss:destroy")
        # now testing:
        item = self.imw[UNPROTECTED]
        item.destroy_all_revisions()
        item = self.imw[PROTECTED]
        with pytest.raises(AccessDenied):
            item.destroy_all_revisions()
