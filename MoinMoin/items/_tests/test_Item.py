# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.items Tests
"""

# TODO: split the tests into multiple files after the items/__init__.py is split.

import pytest

from flask import g as flaskg

from MoinMoin._tests import become_trusted
from MoinMoin.items import Item, ApplicationXTar, NonExistent, Binary, Text, Image, TransformableBitmapImage, MarkupItem
from MoinMoin.config import CONTENTTYPE, ADDRESS, COMMENT, HOSTNAME, USERID, ACTION

class TestItem(object):

    def testNonExistent(self):
        item = Item.create(u'DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.data
        assert meta == {CONTENTTYPE: u'application/x-nonexistent'}
        assert data == ''

    def testClassFinder(self):
        for contenttype, ExpectedClass in [
                (u'application/x-foobar', Binary),
                (u'text/plain', Text),
                (u'text/plain;charset=utf-8', Text),
                (u'image/tiff', Image),
                (u'image/png', TransformableBitmapImage),
            ]:
            item = Item.create(u'foo', contenttype=contenttype)
            assert isinstance(item, ExpectedClass)

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
        saved_meta, saved_data = item.meta, item.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data = rev1_data = data * 10000
        comment = comment + u' again'
        # save rev 1
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[CONTENTTYPE] == contenttype
        assert saved_meta[COMMENT] == comment
        assert saved_data == data

        data = ''
        comment = 'saved empty data'
        # save rev 2 (auto delete)
        item._save(meta, data, comment=comment)
        # check save result
        item = Item.create(name)
        saved_meta, saved_data = dict(item.meta), item.data
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
                              (u'Foo/gh', u'gh', u'text/plain;charset=utf-8'),
                              (u'Foo/ij', u'ij', u'text/plain;charset=utf-8'),
                              (u'Foo/mn', u'mn', u'image/jpeg'),
                             ]
        # check index when startswith param is passed
        flat_index = baseitem.flat_index(startswith=u'a')
        assert flat_index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8')]
        # check index when contenttype_groups is passed
        ctgroups = ["image items"]
        flat_index = baseitem.flat_index(selected_groups=ctgroups)
        assert flat_index == [(u'Foo/mn', u'mn', 'image/jpeg')]
        detailed_index = baseitem.get_detailed_index(baseitem.flat_index())
        assert detailed_index == [(u'Foo/ab', u'ab', 'text/plain;charset=utf-8', False),
                                  (u'Foo/gh', u'gh', 'text/plain;charset=utf-8', False),
                                  (u'Foo/ij', u'ij', 'text/plain;charset=utf-8', True),
                                  (u'Foo/mn', u'mn', 'image/jpeg', False),
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
        become_trusted()
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        # item and its contents before renaming
        assert item.name == u'Test_Item'
        assert item.meta['comment'] == u'saved it'
        Item.rename(item, u'Test_new_Item', comment=u'renamed')
        new_name = u'Test_new_Item'
        item = Item.create(new_name)
        # item and its contents after renaming
        assert item.name == u'Test_new_Item'
        assert item.meta['comment'] == u'renamed'
        assert item.meta['name_old'] == u'Test_Item'
        assert item.data == u'test_data'

    def test_delete(self):
        name = u'Test_Item'
        contenttype = u'text/plain;charset=utf-8'
        data = 'test_data'
        meta = {'test_key': 'test_value', CONTENTTYPE: contenttype}
        comment = u'saved it'
        item = Item.create(name)
        item._save(meta, data, comment=comment)
        item = Item.create(name)
        item.delete(u'item deleted')
        # item and its contents after deletion
        item = Item.create(name)
        assert item.name == u'Test_Item'
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
        item.revert()
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
        # call item.modify
        item.modify()
        item = Item.create(name)
        assert item.name == u'Test_Item'
        with pytest.raises(KeyError):
            item.meta['test_key']


class TestBinary(object):
    """ Test for arbitrary binary items """

    def test_get_templates(self):
        item_name1 = u'Template_Item1'
        item1 = Binary.create(item_name1)
        contenttype1 = u'text/plain'
        meta = {CONTENTTYPE: contenttype1, 'tags': ['template']}
        item1._save(meta)
        item1 = Binary.create(item_name1)

        item_name2 = u'Template_Item2'
        item2 = Binary.create(item_name2)
        contenttype1 = u'text/plain'
        meta = {CONTENTTYPE: contenttype1, 'tags': ['template']}
        item2._save(meta)
        item2 = Binary.create(item_name2)

        item_name3 = u'Template_Item3'
        item3 = Binary.create(item_name3)
        contenttype2 = u'image/png'
        meta = {CONTENTTYPE: contenttype2, 'tags': ['template']}
        item3._save(meta)
        item3 = Binary.create(item_name3)
        # two items of same content type
        result1 = item1.get_templates(contenttype1)
        assert result1 == [item_name1, item_name2]
        # third of different content type
        result2 = item1.get_templates(contenttype2)
        assert result2 == [item_name3]

class TestTarItems(object):
    """
    tests for the container items
    """

    def testCreateContainerRevision(self):
        """
        creates a container and tests the content saved to the container
        """
        item_name = u'ContainerItem1'
        item = Item.create(item_name, contenttype=u'application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        item.put_member('example2.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, contenttype=u'application/x-tar')
        tf_names = set(item.list_members())
        assert tf_names == members
        assert item.get_member('example1.txt').read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        item_name = u'ContainerItem2'
        item = Item.create(item_name, contenttype=u'application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt'])
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)
        filecontent = 'AAAABBBB'
        content_length = len(filecontent)
        item.put_member('example1.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, contenttype=u'application/x-tar')
        assert item.get_member('example1.txt').read() == filecontent

class TestZipMixin(object):
    """ Test for zip-like items """

    def test_put_member(self):
        item_name = u'Zip_file'
        item = Item.create(item_name, contenttype='application/zip')
        filecontent = 'test_contents'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        with pytest.raises(NotImplementedError):
            item.put_member('example1.txt', filecontent, content_length, expected_members=members)

class TestTransformableBitmapImage(object):

    def test__transform(self):
        item_name = u'image_Item'
        item = Binary.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item = Binary.create(item_name)
        try:
            from PIL import Image as PILImage
            with pytest.raises(ValueError):
                result = TransformableBitmapImage._transform(item, 'text/plain')
        except ImportError:
            result = TransformableBitmapImage._transform(item, contenttype)
            assert result == (u'image/jpeg', '')

    def test__render_data_diff(self):
        item_name = u'image_Item'
        item = Binary.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Binary.create(item_name)
        try:
            from PIL import Image as PILImage
            result = TransformableBitmapImage._render_data_diff(item1, item.rev, item1.rev)
            expected = '<img src="/+diffraw/image_Item?rev2=0" />'
            assert str(result) == expected
        except ImportError:
            # no PIL
            pass

    def test__render_data_diff_text(self):
        item_name = u'image_Item'
        item = Binary.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Binary.create(item_name)
        data = 'test_data'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Binary.create(item_name)
        try:
            from PIL import Image as PILImage
            result = TransformableBitmapImage._render_data_diff_text(item1, item1.rev, item2.rev)
            expected = u'The items have different data.'
            assert result == expected
        except ImportError:
            pass

class TestText(object):

    def test_data_conversion(self):
        item_name = u'Text_Item'
        item = Text.create(item_name, u'text/plain')
        test_text = u'This \n is \n a \n Test'
        # test for data_internal_to_form
        result = Text.data_internal_to_form(item, test_text)
        expected = u'This \r\n is \r\n a \r\n Test'
        assert result == expected
        # test for data_form_to_internal
        test_form = u'This \r\n is \r\n a \r\n Test'
        result = Text.data_form_to_internal(item, test_text)
        expected = test_text
        assert result == expected
        # test for data_internal_to_storage
        result = Text.data_internal_to_storage(item, test_text)
        expected = 'This \r\n is \r\n a \r\n Test'
        assert result == expected
        # test for data_storage_to_internal
        data_storage = 'This \r\n is \r\n a \r\n Test'
        result = Text.data_storage_to_internal(item, data_storage)
        expected = test_text
        assert result == expected

    def test__render_data_diff_text(self):
        item_name = u'Text_Item'
        item = Text.create(item_name)
        contenttype = u'text/plain'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Text.create(item_name)
        data = 'test_data'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Text.create(item_name)
        result = Text._render_data_diff_text(item1, item1.rev, item2.rev)
        expected = u'- \n+ test_data'
        assert result == expected
        assert item2.data == ''

    def test__render_data_highlight(self):
        item_name = u'Text_Item'
        item = Text.create(item_name)
        contenttype = u'text/plain'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Text.create(item_name)
        data = 'test_data\nnext line'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Text.create(item_name)
        result = Text._render_data_highlight(item2)
        assert u'<pre class="highlight">test_data\n' in result
        assert item2.data == ''

coverage_modules = ['MoinMoin.items']

