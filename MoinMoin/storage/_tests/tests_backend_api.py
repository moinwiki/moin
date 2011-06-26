# Copyright: 2008 MoinMoin:JohannesBerg
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - storage API
"""

import py

from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError

class TestBackendAPI(object):
    def test_has_item(self):
        class HasNoItemsBackend(Backend):
            def get_item(self, name):
                raise NoSuchItemError('should not be visible')
        be = HasNoItemsBackend()
        assert not be.has_item('asdf')

    def test_unicode_meta(self):
        class HasAnyItemBackend(Backend):
            def get_item(self, name):
                return Item(self, name)
            def _change_item_metadata(self, item):
                pass
            def _get_item_metadata(self, item):
                return {}
            def _publish_item_metadata(self, item):
                pass
        be = HasAnyItemBackend()
        item = be.get_item('a')
        item.change_metadata()
        item[u'a'] = u'b'
        item.publish_metadata()

    def test_reserved_metadata(self):
        class ReservedMetaDataBackend(Backend):
            def get_item(self, name):
                return Item(self, name)
            def _change_item_metadata(self, item):
                pass
            def _get_item_metadata(self, item):
                return {'__asdf': 'xx'}
            def _publish_item_metadata(self, item):
                pass
            def _get_revision(self, item, revno):
                assert revno == 0
                return StoredRevision(item, revno)
            def _create_revision(self, item, revno):
                assert revno == 1
                return NewRevision(item, revno)
            def _rollback_item(self, item):
                pass
            def _get_revision_metadata(self, rev):
                return {'__asdf': 'xx'}
            def _list_revisions(self, item):
                return [0]

        be = ReservedMetaDataBackend()
        item = be.get_item('a')
        assert not item.keys()

        oldrev = item.get_revision(0)
        assert not oldrev.keys()

        newrev = item.create_revision(1)
        py.test.raises(TypeError, newrev.__setitem__, '__reserved')

        assert not newrev.keys()

        newrev['a'] = 'b'
        assert newrev['a'] == 'b'

        item.rollback()
