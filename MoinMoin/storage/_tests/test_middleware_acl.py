# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - ACLMiddleWare

    This defines tests for the ACLMiddleWare
"""


import py

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
        name = "noaccess"
        self.create_item_acl(name, "All:")
        assert py.test.raises(AccessDeniedError, self.get_item, name)

    def test_create_item(self):
        class Config(wikiconfig.Config):
            # no create
            content_acl = dict(default=u"All:admin,read,write,destroy")

        backend = flaskg.storage
        assert py.test.raises(AccessDeniedError, backend.create_item, "I will never exist")

        item = self.create_item_acl("i will exist!", "All:read,write")
        rev = item.create_revision(1)
        data = "my very existent data"
        rev.write(data)
        item.commit()
        assert item.get_revision(1).read() == data

    def test_read_access_allowed(self):
        name = "readaccessallowed"
        self.create_item_acl(name, "All:read")
        # Should simply pass...
        item = self.get_item(name)

        # Should not...
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)
        assert py.test.raises(AccessDeniedError, item.change_metadata)

    def test_write_after_create(self):
        name = "writeaftercreate"
        item = self.create_item_acl(name, "All:")
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)

    def test_modify_without_acl_change(self):
        name = "copy_without_acl_change"
        acl = "All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        # This should pass
        rev[ACL] = acl
        item.commit()

    def test_copy_with_acl_change(self):
        name = "copy_with_acl_change"
        acl = "All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        py.test.raises(AccessDeniedError, rev.__setitem__, ACL, acl + ",write")

    def test_write_without_read(self):
        name = "write_but_not_read"
        acl = "All:write"
        item = flaskg.storage.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        rev.write("My name is " + name)
        item.commit()

        py.test.raises(AccessDeniedError, item.get_revision, -1)
        py.test.raises(AccessDeniedError, item.get_revision, 0)

