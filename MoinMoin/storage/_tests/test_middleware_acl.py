# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - ACLMiddleWare

    This defines tests for the ACLMiddleWare
"""


import pytest

from flask import g as flaskg

from MoinMoin.config import ACL
from MoinMoin.storage.error import AccessDeniedError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin._tests import wikiconfig


class TestACLMiddleware(BackendTest):
    class Config(wikiconfig.Config):
        content_acl = dict(default=u"All:admin,read,write,destroy,create")


    def create_backend(self):
        # Called before *each* testcase. Provides fresh backends every time.
        return flaskg.storage

    def kill_backend(self):
        pass


    def get_item(self, name):
        # Just as a shortcut
        return flaskg.storage.get_item(name)

    def create_item_acl(self, name, acl):
        item = flaskg.storage.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        item.commit()
        return item


    def test_noaccess(self):
        name = u"noaccess"
        self.create_item_acl(name, u"All:")
        assert pytest.raises(AccessDeniedError, self.get_item, name)

    def test_create_item(self):
        class Config(wikiconfig.Config):
            # no create
            content_acl = dict(default=u"All:admin,read,write,destroy")

        backend = flaskg.storage
        assert pytest.raises(AccessDeniedError, backend.create_item, u"I will never exist")

        item = self.create_item_acl(u"i will exist!", u"All:read,write")
        rev = item.create_revision(1)
        data = "my very existent data"
        rev.write(data)
        item.commit()
        assert item.get_revision(1).read() == data

    def test_read_access_allowed(self):
        name = u"readaccessallowed"
        self.create_item_acl(name, u"All:read")
        # Should simply pass...
        item = self.get_item(name)

        # Should not...
        assert pytest.raises(AccessDeniedError, item.create_revision, 1)
        assert pytest.raises(AccessDeniedError, item.change_metadata)

    def test_write_after_create(self):
        name = u"writeaftercreate"
        item = self.create_item_acl(name, u"All:")
        assert pytest.raises(AccessDeniedError, item.create_revision, 1)

    def test_modify_without_acl_change(self):
        name = u"copy_without_acl_change"
        acl = u"All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        # This should pass
        rev[ACL] = acl
        item.commit()

    def test_copy_with_acl_change(self):
        name = u"copy_with_acl_change"
        acl = u"All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        # without admin rights it is disallowed to change ACL
        pytest.raises(AccessDeniedError, rev.__setitem__, ACL, acl + u",destroy")

    def test_write_without_read(self):
        name = u"write_but_not_read"
        acl = u"All:write"
        item = flaskg.storage.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        rev.write("My name is " + name)
        item.commit()

        pytest.raises(AccessDeniedError, item.get_revision, -1)
        pytest.raises(AccessDeniedError, item.get_revision, 0)

