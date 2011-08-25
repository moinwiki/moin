# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - RouterBackend

    This defines tests for the RouterBackend
"""

import os

import pytest

from flask import current_app as app

from MoinMoin.config import NAME
from MoinMoin.error import ConfigurationError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage.backends.router import RouterBackend
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


    def test_history(self):
        order = [(u'first', 0, ), (u'second', 0, ), (u'first', 1, ), (u'a', 0), (u'child/my_subitem', 0) ]
        for name, revno in order:
            if revno == 0:
                item = self.backend.create_item(name)
            else:
                item = self.backend.get_item(name)
            item.create_revision(revno)
            item.commit()

            # Revisions are created too fast for the rev's timestamp's granularity.
            # This only affects the RouterBackend because there several different
            # backends are used and no means for storing simultaneously created revs
            # in the correct order exists between backends. It affects AclWrapperBackend
            # tests as well because those use a RouterBackend internally for real-world-likeness.

            # XXX XXX
            # You may have realized that all the items above belong to the same backend so this shouldn't actually matter.
            # It does matter, however, once you consider that the RouterBackend uses the generic, slow history implementation.
            # This one uses iteritems and then sorts all the revisions itself, hence discarding any information of ordering
            # for simultaneously created revisions. If we just call history of that single backend directly, it works without
            # time.sleep. For n backends, however, you'd have to somehow merge the revisions into one generator again, thus
            # discarding that information again. Besides, that would be a costly operation. The ordering for simultaneosly
            # created revisions remains the same since it's based on tuple ordering. Better proposals welcome.
            import time
            time.sleep(1)

        for num, doc in enumerate(self.backend.history(reverse=False)):
            name, revno = order[num]
            assert doc[NAME] == name
            assert doc["rev_no"] == revno

        order.reverse()
        for num, doc in enumerate(self.backend.history(reverse=True)):
            name, revno = order[num]
            assert doc[NAME] == name
            assert doc["rev_no"] == revno

    def test_history_size_after_rename(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.rename(u'second')
        item.create_revision(1)
        item.commit()
        assert len(list(self.backend.history())) == 2

    def test_history_after_destroy_item(self):
        itemname = u"I will be completely destroyed"
        rev_data = "I will be completely destroyed, too, hopefully"
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        rev.write(rev_data)
        item.commit()

        item.destroy()

        itemnames_history = [doc[NAME] for doc in self.backend.history()]
        assert itemname not in itemnames_history

    def test_history_after_destroy_revision(self):
        itemname = u"I will see my children die"
        rev_data = "I will die!"
        persistent_rev = "I will see my sibling die :-("
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        rev.write(rev_data)
        item.commit()
        rev = item.create_revision(1)
        rev.write(persistent_rev)
        item.commit()

        rev = item.get_revision(0)
        rev.destroy()

        itemnames_revs_history = [(doc[NAME], doc["rev_no"]) for doc in self.backend.history()]
        assert (itemname, 0) not in itemnames_revs_history

    def test_history_item_names(self):
        item = self.backend.create_item(u'first')
        item.create_revision(0)
        item.commit()
        item.rename(u'second')
        item.create_revision(1)
        item.commit()
        docs_history = list(self.backend.history(reverse=False))
        assert docs_history[0]["rev_no"] == 0
        assert docs_history[0][NAME] == u'first'
        assert docs_history[1]["rev_no"] == 1
        assert docs_history[1][NAME] == u'second'

