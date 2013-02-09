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
from MoinMoin.items import Item, NonExistent, IndexEntry, MixedIndexEntry
from MoinMoin.items.content import Binary, Text, Image, TransformableBitmapImage, MarkupItem
from MoinMoin.constants.keys import ITEMTYPE, CONTENTTYPE, NAME, ADDRESS, COMMENT, HOSTNAME, USERID, ACTION


def build_index(basename, relnames):
    """
    Build a list of IndexEntry by hand, useful as a test helper.
    """
    return [(IndexEntry(relname, Item.create('/'.join((basename, relname))).meta))
            for relname in relnames]

def build_mixed_index(basename, spec):
    """
    Build a list of MixedIndexEntry by hand, useful as a test helper.

    :spec is a list of (relname, hassubitem) tuples.
    """
    return [(MixedIndexEntry(relname, Item.create('/'.join((basename, relname))).meta, hassubitem))
            for relname, hassubitem in spec]


class TestItem(object):

    def _testNonExistent(self):
        item = Item.create(u'DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.content.data
        assert meta == {
                ITEMTYPE: u'nonexistent',
                CONTENTTYPE: u'application/x-nonexistent',
                NAME: u'DoesNotExist',
                }
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

        baseitem = Item.create(basename)

        # test Item.make_flat_index
        # TODO: test Item.get_subitem_revs
        dirs, files = baseitem.get_index()
        assert dirs == build_index(basename, [u'cd', u'ij'])
        assert files == build_index(basename, [u'ab', u'gh', u'ij', u'mn'])

        # test Item.get_mixed_index
        mixed_index = baseitem.get_mixed_index()
        assert mixed_index == build_mixed_index(basename, [
            (u'ab', False),
            (u'cd', True),
            (u'gh', False),
            (u'ij', True),
            (u'mn', False),
        ])

        # check filtered index when startswith param is passed
        dirs, files = baseitem.get_index(startswith=u'a')
        assert dirs == []
        assert files == build_index(basename, [u'ab'])

        # check filtered index when contenttype_groups is passed
        ctgroups = ["other text items"]
        dirs, files = baseitem.get_index(selected_groups=ctgroups)
        assert dirs == build_index(basename, [u'cd', u'ij'])
        assert files == build_index(basename, [u'ab', u'gh', u'ij'])

    def test_meta_filter(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        meta = {'test_key': 'test_val', CONTENTTYPE: contenttype, NAME: [u'test_name'], 'address': u'1.2.3.4'}
        item = Item.create(name)
        result = Item.meta_filter(item, meta)
        # keys like NAME, ITEMID, REVID, DATAID are filtered
        expected = {'test_key': 'test_val', CONTENTTYPE: contenttype, NAME: [u'test_name']}
        assert result == expected

    def test_meta_dict_to_text(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        meta = {'test_key': 'test_val', CONTENTTYPE: contenttype, NAME: [u'test_name']}
        item = Item.create(name)
        result = Item.meta_dict_to_text(item, meta)
        expected = '{\n  "contenttype": "text/plain;charset=utf-8", \n  "name": [\n    "test_name"\n  ], \n  "test_key": "test_val"\n}'
        assert result == expected

    def test_meta_text_to_dict(self):
        name = u'Test_item'
        contenttype = u'text/plain;charset=utf-8'
        text = '{\n  "contenttype": "text/plain;charset=utf-8", \n  "test_key": "test_val", \n "name": ["test_name"] \n}'
        item = Item.create(name)
        result = Item.meta_text_to_dict(item, text)
        expected = {'test_key': 'test_val', CONTENTTYPE: contenttype, NAME: [u"test_name"]}
        assert result == expected

    def test_item_can_have_several_names(self):
        content = u"This is page content"

        update_item(u'Page',
                    {NAME: [u'Page',
                            u'Another name',
                            ],
                     CONTENTTYPE: u'text/x.moin.wiki'}, content)

        item1 = Item.create(u'Page')
        assert item1.name == u'Page'
        assert item1.meta[CONTENTTYPE] == 'text/x.moin.wiki'
        assert item1.content.data == content

        item2 = Item.create(u'Another name')
        assert item2.name == u'Another name'
        assert item2.meta[CONTENTTYPE] == 'text/x.moin.wiki'
        assert item2.content.data == content

        assert item1.rev.revid == item2.rev.revid

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
        assert item.meta['name_old'] == [u'Test_Item']
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'test_data'

    def test_rename_acts_only_in_active_name_in_case_there_are_several_names(self):
        content = u"This is page content"

        update_item(u'Page',
                    {NAME: [u'First',
                            u'Second',
                            u'Third',
                            ],
                     CONTENTTYPE: u'text/x.moin.wiki'}, content)

        item = Item.create(u'Second')
        item.rename(u'New name', comment=u'renamed')

        item1 = Item.create(u'First')
        assert item1.name == u'First'
        assert item1.meta[CONTENTTYPE] == 'text/x.moin.wiki'
        assert item1.content.data == content

        item2 = Item.create(u'New name')
        assert item2.name == u'New name'
        assert item2.meta[CONTENTTYPE] == 'text/x.moin.wiki'
        assert item2.content.data == content

        item3 = Item.create(u'Third')
        assert item3.name == u'Third'
        assert item3.meta[CONTENTTYPE] == 'text/x.moin.wiki'
        assert item3.content.data == content

        assert item1.rev.revid == item2.rev.revid == item3.rev.revid

        item4 = Item.create(u'Second')
        assert item4.meta[CONTENTTYPE] == 'application/x-nonexistent'

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
        assert item.meta['name_old'] == [u'Page']
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'Page 1'

        item = Item.create(u'Renamed_Page/Child')
        assert item.name == u'Renamed_Page/Child'
        assert item.meta['name_old'] == [u'Page/Child']
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'this is child'

        item = Item.create(u'Renamed_Page/Child/Another')
        assert item.name == u'Renamed_Page/Child/Another'
        assert item.meta['name_old'] == [u'Page/Child/Another']
        assert item.meta['comment'] == u'renamed'
        assert item.content.data == u'another child'

    def test_rename_recursion_with_multiple_names_and_children(self):
        update_item(u'Foo',
                    {CONTENTTYPE: u'text/x.moin.wiki',
                         NAME: [u'Other', u'Page', u'Foo']},
                    u'Parent')
        update_item(u'Page/Child', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Child of Page')
        update_item(u'Other/Child2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Child of Other')
        update_item(u'Another',
                    {CONTENTTYPE: u'text/x.moin.wiki',
                     NAME: [u'Another', u'Page/Second']
                         },
                    u'Both')
        update_item(u'Page/Second/Child', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Child of Second')
        update_item(u'Another/Child', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Child of Another')

        item = Item.create(u'Page')

        item.rename(u'Renamed', comment=u'renamed')

        assert Item.create(u'Page/Child').meta[CONTENTTYPE] == 'application/x-nonexistent'
        assert Item.create(u'Renamed/Child').content.data == u'Child of Page'
        assert Item.create(u'Page/Second').meta[CONTENTTYPE] == 'application/x-nonexistent'
        assert Item.create(u'Renamed/Second').content.data == u'Both'
        assert Item.create(u'Another').content.data == u'Both'
        assert Item.create(u'Page/Second/Child').meta[CONTENTTYPE] == 'application/x-nonexistent'
        assert Item.create(u'Renamed/Second/Child').content.data == u'Child of Second'
        assert Item.create(u'Other/Child2').content.data == u'Child of Other'
        assert Item.create(u'Another/Child').content.data == u'Child of Another'

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
