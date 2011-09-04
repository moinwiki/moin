# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - RouterBackend

    This defines tests for the RouterBackend
"""

import os
import time

import pytest

from flask import current_app as app

from whoosh.query import Term, And, Every

from MoinMoin.config import NAME, MTIME
from MoinMoin.error import ConfigurationError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage.middleware.router import RouterBackend
from MoinMoin.search.indexing import WhooshIndex

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
        return RouterBackend(self.mapping, cfg=app.cfg)

    def kill_backend(self):
        pass

    def teardown_method(self, method):
        # clean the index directory after each test as messes with the backend history
        # XXX tests with backend.history should not be failing due to contents in index directory
        # the contents of the directory and the way backend.history is handled should be implemented
        # in a better way
        index_dir = WhooshIndex()._index_dir
        for values in os.walk(index_dir):
            for index_file_name in values[2]:
                index_file = index_dir + '/' + index_file_name
                os.remove(index_file)

    def test_correct_backend(self):
        mymap = {u'rootitem': self.root,         # == /rootitem
                 u'child/joe': self.child,       # Direct child of namespace.
                 u'other/jane': self.other,      # Direct child of namespace.
                 u'child/': self.child,          # Root of namespace itself (!= root)
                 u'other/': self.other,          # Root of namespace
                 u'': self.root,                 # Due to lack of any namespace info
                }

        assert not (self.root is self.child is self.other)
        for itemname, backend in mymap.iteritems():
            assert self.backend._get_backend(itemname)[0] is backend

    def test_store_and_get(self):
        itemname = u'child/foo'
        item = self.backend.create_item(itemname)
        assert item.name == itemname
        # using item._backend to get the backend makes this test fail.
        test_backend, child_name, root_name = item._get_backend(itemname)
        assert test_backend is self.child
        item.change_metadata()
        item[u'just'] = u'testing'
        item.publish_metadata()
        # using item._backend to get the backend makes this test fail.
        test_backend, child_name, root_name = item._get_backend(itemname)
        assert test_backend is self.child
        assert item[u'just'] == u'testing'
        assert item.name == itemname

    def test_traversal(self):
        mymap = {u'rootitem': self.root,         # == /rootitem
                 u'child/joe': self.child,       # Direct child of namespace.
                 u'other/jane': self.other,      # Direct child of namespace.
                 u'child/': self.child,          # Root of namespace itself (!= root)
                 u'other/': self.other,          # Root of namespace
                 u'': self.root,                 # Due to lack of any namespace info
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
        userid = u'1249291178.45.20407'
        user = self.backend.create_item(self.ns_user_profile + userid)
        user.change_metadata()
        user[u"name"] = u"joe"
        user.publish_metadata()

        all_items = list(self.backend.iteritems())
        all_items = [item.name for item in all_items]
        assert (self.ns_user_profile + userid) in all_items
        assert self.backend.has_item(self.ns_user_profile + userid)

    def test_nonexisting_namespace(self):
        itemname = u'nonexisting/namespace/somewhere/deep/below'
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        item.commit()
        assert self.root.has_item(itemname)

    def test_cross_backend_rename(self):
        itemname = u'i_will_be_moved'
        item = self.backend.create_item(u'child/' + itemname)
        item.create_revision(0)
        item.commit()
        assert self.child.has_item(itemname)
        newname = u'i_was_moved'
        item.rename(u'other/' + newname)
        print [item.name for item in self.child.iteritems()]
        assert not self.child.has_item(itemname)
        assert not self.child.has_item(newname)
        assert not self.child.has_item(u'other/' + newname)
        assert self.other.has_item(newname)

    def test_itemname_equals_namespace(self):
        itemname = u'child'
        backend, name, mountpoint = self.backend._get_backend(itemname)
        assert backend is self.child
        assert name == ''
        assert mountpoint == 'child'

    def test_search_item_history_order(self):
        item_name = u'some item'
        item = self.backend.create_item(item_name)
        for rev_no in range(3):
            rev = item.create_revision(rev_no)
            item.commit()
        query = Term("name_exact", item_name)
        results = list(self.backend.search(query, all_revs=True, sortedby="rev_no"))
        print results
        assert results[0].get("rev_no") == 0
        assert results[1].get("rev_no") == 1
        assert results[2].get("rev_no") == 2
        results = list(self.backend.search(query, all_revs=True, sortedby="rev_no", reverse=True))
        print results
        assert results[0].get("rev_no") == 2
        assert results[1].get("rev_no") == 1
        assert results[2].get("rev_no") == 0

    def test_search_global_history_order(self):
        names = [u'foo', u'bar', u'baz', ]
        for item_name in names:
            item = self.backend.create_item(item_name)
            rev = item.create_revision(0)
            item.commit()
            time.sleep(1) # make sure we have different MTIME
        query = Every()
        results = list(self.backend.search(query, all_revs=True, sortedby=[MTIME, "rev_no"]))
        print results
        assert results[0].get(NAME) == names[0]
        assert results[1].get(NAME) == names[1]
        assert results[2].get(NAME) == names[2]
        results = list(self.backend.search(query, all_revs=True, sortedby=[MTIME, "rev_no"], reverse=True))
        print results
        assert results[0].get(NAME) == names[2]
        assert results[1].get(NAME) == names[1]
        assert results[2].get(NAME) == names[0]


