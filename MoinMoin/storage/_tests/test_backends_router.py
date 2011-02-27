# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - RouterBackend

    This defines tests for the RouterBackend
"""


import py

from flask import current_app as app

from MoinMoin.error import ConfigurationError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage.backends.router import RouterBackend

class TestRouterBackend(BackendTest):
    """
    Test the MemoryBackend
    """

    def create_backend(self):
        self.root = MemoryBackend()
        self.ns_user_profile = app.cfg.ns_user_profile
        self.users = MemoryBackend()
        self.child = MemoryBackend()
        self.other = MemoryBackend()
        self.mapping = [('child', self.child), ('other/', self.other), (self.ns_user_profile, self.users), ('/', self.root)]
        return RouterBackend(self.mapping, index_uri='sqlite://')

    def kill_backend(self):
        pass


    def test_correct_backend(self):
        mymap = {'rootitem': self.root,         # == /rootitem
                 'child/joe': self.child,       # Direct child of namespace.
                 'other/jane': self.other,      # Direct child of namespace.
                 'child/': self.child,          # Root of namespace itself (!= root)
                 'other/': self.other,          # Root of namespace
                 '': self.root,                 # Due to lack of any namespace info
                }

        assert not (self.root is self.child is self.other)
        for itemname, backend in mymap.iteritems():
            assert self.backend._get_backend(itemname)[0] is backend

    def test_store_and_get(self):
        itemname = 'child/foo'
        item = self.backend.create_item(itemname)
        assert item.name == itemname
        assert item._backend is self.child
        item.change_metadata()
        item['just'] = 'testing'
        item.publish_metadata()

        item = self.backend.get_item(itemname)
        assert item._backend is self.child
        assert item['just'] == 'testing'
        assert item.name == itemname

    def test_traversal(self):
        mymap = {'rootitem': self.root,         # == /rootitem
                 'child/joe': self.child,       # Direct child of namespace.
                 'other/jane': self.other,      # Direct child of namespace.
                 'child/': self.child,          # Root of namespace itself (!= root)
                 'other/': self.other,          # Root of namespace
                 '': self.root,                 # Due to lack of any namespace info
                }

        items_in = []
        for itemname, backend in mymap.iteritems():
            item = self.backend.create_item(itemname)
            assert item.name == itemname
            rev = item.create_revision(0)
            rev.write("This is %s" % itemname)
            item.commit()
            items_in.append(item)
            assert self.backend.has_item(itemname)

        items_out = list(self.backend.iteritems())

        items_in = [item.name for item in items_in]
        items_out = [item.name for item in items_out]
        items_in.sort()
        items_out.sort()

        assert items_in == items_out

    def test_user_in_traversal(self):
        userid = '1249291178.45.20407'
        user = self.backend.create_item(self.ns_user_profile + userid)
        user.change_metadata()
        user["name"] = "joe"
        user.publish_metadata()

        all_items = list(self.backend.iteritems())
        all_items = [item.name for item in all_items]
        assert (self.ns_user_profile + userid) in all_items
        assert self.backend.has_item(self.ns_user_profile + userid)

    def test_nonexisting_namespace(self):
        itemname = 'nonexisting/namespace/somewhere/deep/below'
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        item.commit()
        assert self.root.has_item(itemname)

    def test_cross_backend_rename(self):
        itemname = 'i_will_be_moved'
        item = self.backend.create_item('child/' + itemname)
        item.create_revision(0)
        item.commit()
        assert self.child.has_item(itemname)
        newname = 'i_was_moved'
        item.rename('other/' + newname)
        print [item.name for item in self.child.iteritems()]
        assert not self.child.has_item(itemname)
        assert not self.child.has_item(newname)
        assert not self.child.has_item('other/' + newname)
        assert self.other.has_item(newname)

    def test_itemname_equals_namespace(self):
        itemname = 'child'
        backend, name, mountpoint = self.backend._get_backend(itemname)
        assert backend is self.child
        assert name == ''
        assert mountpoint == 'child'
