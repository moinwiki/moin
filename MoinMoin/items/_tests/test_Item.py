# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.items Tests
"""

import pytest

from flask import g as flaskg
from flask import Markup

from werkzeug import escape

from MoinMoin.util import diff_html

from MoinMoin._tests import become_trusted, update_item
from MoinMoin.items import Item, NonExistent
from MoinMoin.items.content import Binary, Text, Image, TransformableBitmapImage, MarkupItem
from MoinMoin.config import CONTENTTYPE, ADDRESS, COMMENT, HOSTNAME, USERID, ACTION

class TestItem(object):

    def testNonExistent(self):
        item = Item.create(u'DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.content.data
        assert meta == {CONTENTTYPE: u'application/x-nonexistent'}
        assert data == ''

    def testCRUD(self):
        name = u'NewItem'
        contenttype = u'text/plain;charset=utf-8'
        data = 'foobar'
        meta = {'foo': 'bar', CONTENTTYPE: contenttype}
        comment = u'saved it'
        become_trusted()
        item = Item.create(name)
        # save rev 0
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = item.meta, item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data = rev1_data = data * 10000
        comment = comment + u' again'
        # save rev 1
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data = ''
        comment = 'saved empty data'
        # save rev 2 (auto delete)
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.content.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

    def testIndex(self):
        # create a toplevel and some sub-items
        basename = u'Foo'
        for name in ['', '/ab', '/cd/ef', '/gh', '/ij', '/ij/kl', ]:
            item = Item.create(basename + name)
            item._save({CONTENTTYPE: u'text/plain;charset=utf-8'}, "foo")
        item = Item.create(basename + '/mn')
        item._save({CONTENTTYPE: u'image/jpeg'}, "JPG")
        # check index
        baseitem = Item.create(basename)
        index = baseitem.get_index()
        assert index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8'),
                         (u'Foo/cd/ef', u'cd/ef', 'text/plain;charset=utf-8'),
                         (u'Foo/gh', u'gh', 'text/plain;charset=utf-8'),
                         (u'Foo/ij', u'ij', 'text/plain;charset=utf-8'),
                         (u'Foo/ij/kl', u'ij/kl', 'text/plain;charset=utf-8'),
                         (u'Foo/mn', u'mn', 'image/jpeg'),
                        ]
        flat_index = baseitem.flat_index()
        assert flat_index == [(u'Foo/ab', u'ab', u'text/plain;charset=utf-8'),
                              (u'Foo/cd', u'cd', u'application/x-nonexistent'),
                              (u'Foo/gh', u'gh', u'text/plain;charset=utf-8'),
                              (u'Foo/ij', u'ij', u'text/plain;charset=utf-8'),
                              (u'Foo/mn', u'mn', u'image/jpeg'),
                             ]
        # check index when startswith param is passed
        flat_index = baseitem.flat_index(startswith=u'a')
        assert flat_index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8')]

        #check that virtual container item is returned with startswith
        flat_index = baseitem.flat_index(startswith=u'c')
        assert flat_index == [(u'Foo/cd', u'cd', u'application/x-nonexistent')]

        # check index when contenttype_groups is passed
        ctgroups = ["image items"]
        flat_index = baseitem.flat_index(selected_groups=ctgroups)
        assert flat_index == [(u'Foo/mn', u'mn', 'image/jpeg')]

        # If we ask for text/plain type, should Foo/cd be returned?

        # check detailed index
        detailed_index = baseitem.get_detailed_index(baseitem.flat_index())
        assert detailed_index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8', False),
                                  (u'Foo/cd', u'cd', 'application/x-nonexistent', True),
                                  (u'Foo/gh', u'gh', 'text/plain;charset=utf-8', False),
                                  (u'Foo/ij', u'ij', 'text/plain;charset=utf-8', True),
                                  (u'Foo/mn', u'mn', 'image/jpeg', False),
                                  ]

    def testIndexOnDisconnectedLevels(self):
        # create a toplevel and some sub-items
        basename = u'Bar'
        for name in ['', '/ab', '/ab/cd/ef/gh', '/ij/kl/mn/op', '/ij/kl/rs']:
            item = Item.create(basename + name)
            item._save({CONTENTTYPE: u'text/plain;charset=utf-8'}, "foo")

        baseitem = Item.create(basename)
        index = baseitem.get_index()
        index = baseitem._connect_levels(index)

        assert index == [(u'Bar/ab', u'ab', u'text/plain;charset=utf-8'),
                         (u'Bar/ab/cd', u'ab/cd', u'application/x-nonexistent'),
                         (u'Bar/ab/cd/ef', u'ab/cd/ef', u'application/x-nonexistent'),
                         (u'Bar/ab/cd/ef/gh', u'ab/cd/ef/gh', u'text/plain;charset=utf-8'),
                         (u'Bar/ij', u'ij', u'application/x-nonexistent'),
                         (u'Bar/ij/kl', u'ij/kl', u'application/x-nonexistent'),
                         (u'Bar/ij/kl/mn', u'ij/kl/mn', u'application/x-nonexistent'),
                         (u'Bar/ij/kl/mn/op', u'ij/kl/mn/op', u'text/plain;charset=utf-8'),
                         (u'Bar/ij/kl/rs', u'ij/kl/rs', u'text/plain;charset=utf-8')]

        flat_index = baseitem.flat_index()
        assert flat_index == [(u'Bar/ab', u'ab', u'text/plain;charset=utf-8'),
                              (u'Bar/ij', u'ij', u'application/x-nonexistent'),
                             ]

    def test_meta_filter(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        meta = {'test_key': 'test_val', CONTENTTYPE: contenttype, 'name': 'test_name'}
        item = Item.create(name)
        result = Item.meta_filter(item, meta)
        # keys like NAME, ITEMID, REVID, DATAID are filtered
        expected = {'test_key': 'test_val', CONTENTTYPE: contenttype}
        assert result == expected

    def test_meta_dict_to_text(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        meta = {'test_key': 'test_val', CONTENTTYPE: contenttype, 'name': 'test_name'}
        item = Item.create(name)
        result = Item.meta_dict_to_text(item, meta)
        expected = '{\n  "contenttype": "text/plain;charset=utf-8", \n  "test_key": "test_val"\n}'
        assert result == expected

    def test_meta_text_to_dict(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        text = '{\n  "contenttype": "text/plain;charset=utf-8", \n  "test_key": "test_val", \n "name": "test_name" \n}'
        item = Item.create(name)
        result = Item.meta_text_to_dict(item, text)
        expected = {'test_key': 'test_val', CONTENTTYPE: contenttype}
        assert result == expected

    def test_rename(self):
        name = u'Test_Item'
        contenttype = u'text/plain;charset=utf-8'
        data = 'test_data'
        meta = {'test_key': 'test_value', CONTENTTYPE: contenttype}
        comment = u'saved it'
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        # item and its contents before renaming
        item = Item.create(name)
        assert item.name == u'Test_Item'
        assert item.meta['comment'] == u'saved it'
        new_name = u'Test_new_Item'
        item.rename(new_name, comment=u'renamed')
        # item at original name and its contents after renaming
        item = Item.create(name)
        assert item.name == u'Test_Item'
        # this should be a fresh, new item, NOT the stuff we renamed:
        assert item.meta[CONTENTTYPE] == 'application/x-nonexistent'
        # item at new name and its contents after renaming
        item = Item.create(new_name)
        assert item.name == u'Test_new_Item'
        assert item.meta['name_old'] == u'Test_Item'
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'test_data'

    def test_rename_recursion(self):
        update_item(u'Page', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Page 1')
        update_item(u'Page/Child', {CONTENTTYPE: u'text/x.moin.wiki'}, u'this is child')
        update_item(u'Page/Child/Another', {CONTENTTYPE: u'text/x.moin.wiki'}, u'another child')

        item = Item.create(u'Page')
        item.rename(u'Renamed_Page', comment=u'renamed')

        # items at original name and its contents after renaming
        item = Item.create(u'Page')
        assert item.name == u'Page'
        assert item.meta[CONTENTTYPE] == 'application/x-nonexistent'
        item = Item.create(u'Page/Child')
        assert item.name == u'Page/Child'
        assert item.meta[CONTENTTYPE] == 'application/x-nonexistent'
        item = Item.create(u'Page/Child/Another')
        assert item.name == u'Page/Child/Another'
        assert item.meta[CONTENTTYPE] == 'application/x-nonexistent'

        # item at new name and its contents after renaming
        item = Item.create(u'Renamed_Page')
        assert item.name == u'Renamed_Page'
        assert item.meta['name_old'] == u'Page'
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'Page 1'

        item = Item.create(u'Renamed_Page/Child')
        assert item.name == u'Renamed_Page/Child'
        assert item.meta['name_old'] == u'Page/Child'
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'this is child'

        item = Item.create(u'Renamed_Page/Child/Another')
        assert item.name == u'Renamed_Page/Child/Another'
        assert item.meta['name_old'] == u'Page/Child/Another'
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'another child'

    def test_delete(self):
        name = u'Test_Item2'
        contenttype = u'text/plain;charset=utf-8'
        data = 'test_data'
        meta = {'test_key': 'test_value', CONTENTTYPE: contenttype}
        comment = u'saved it'
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        # item and its contents before deleting
        item = Item.create(name)
        assert item.name == u'Test_Item2'
        assert item.meta['comment'] == u'saved it'
        item.delete(u'deleted')
        # item and its contents after deletion
        item = Item.create(name)
        assert item.name == u'Test_Item2'
        # this should be a fresh, new item, NOT the stuff we deleted:
        assert item.meta[CONTENTTYPE] == 'application/x-nonexistent'

    def test_revert(self):
        name = u'Test_Item'
        contenttype = u'text/plain;charset=utf-8'
        data = 'test_data'
        meta = {'test_key': 'test_value', CONTENTTYPE: contenttype}
        comment = u'saved it'
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        item.revert(u'revert')
        item = Item.create(name)
        assert item.meta['action'] == u'REVERT'

    def test_modify(self):
        name = u'Test_Item'
        contenttype = u'text/plain;charset=utf-8'
        data = 'test_data'
        meta = {'test_key': 'test_value', CONTENTTYPE: contenttype}
        comment = u'saved it'
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        assert item.name == u'Test_Item'
        assert item.meta['test_key'] == 'test_value'
        # modify
        another_data = 'another_test_data'
        another_meta = {'another_test_key': 'another_test_value'}
        item.modify(another_meta, another_data)
        item = Item.create(name)
        assert item.name == u'Test_Item'
        with pytest.raises(KeyError):
            item.meta['test_key']
        assert item.meta['another_test_key'] == another_meta['another_test_key']
        assert item.content.data == another_data

coverage_modules = ['MoinMoin.items']
