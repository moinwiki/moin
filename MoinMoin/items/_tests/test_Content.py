# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# TODO: Split tests for Content subclasses after the subclasses themselves are
# split

"""
    MoinMoin - MoinMoin.items.content Tests
"""

import pytest

from flask import Markup

from werkzeug import escape

from MoinMoin.util import diff_html

from MoinMoin._tests import become_trusted, update_item
from MoinMoin.items import Item
from MoinMoin.items.content import Content, ApplicationXTar, Binary, Text, Image, TransformableBitmapImage, MarkupItem
from MoinMoin.constants.keys import CONTENTTYPE, TAGS
from MoinMoin.constants.itemtypes import ITEMTYPE_DEFAULT


class TestContent(object):
    """ Test for arbitrary content """

    def testClassFinder(self):
        for contenttype, ExpectedClass in [
                (u'application/x-foobar', Binary),
                (u'text/plain', Text),
                (u'text/plain;charset=utf-8', Text),
                (u'image/tiff', Image),
                (u'image/png', TransformableBitmapImage),
            ]:
            content = Content.create(contenttype)
            assert isinstance(content, ExpectedClass)

    def test_get_templates(self):
        item_name1 = u'Template_Item1'
        item1 = Item.create(item_name1)
        contenttype1 = u'text/plain'
        meta = {CONTENTTYPE: contenttype1, TAGS: ['template']}
        item1._save(meta)
        item1 = Item.create(item_name1)

        item_name2 = u'Template_Item2'
        item2 = Item.create(item_name2)
        contenttype1 = u'text/plain'
        meta = {CONTENTTYPE: contenttype1, TAGS: ['template']}
        item2._save(meta)
        item2 = Item.create(item_name2)

        item_name3 = u'Template_Item3'
        item3 = Item.create(item_name3)
        contenttype2 = u'image/png'
        meta = {CONTENTTYPE: contenttype2, TAGS: ['template']}
        item3._save(meta)
        item3 = Item.create(item_name3)
        # two items of same content type
        result1 = item1.content.get_templates(contenttype1)
        assert result1 == [item_name1, item_name2]
        # third of different content type
        result2 = item1.content.get_templates(contenttype2)
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
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype=u'application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        item.content.put_member('example1.txt', filecontent, content_length, expected_members=members)
        item.content.put_member('example2.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype=u'application/x-tar')
        tf_names = set(item.content.list_members())
        assert tf_names == members
        assert item.content.get_member('example1.txt').read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        item_name = u'ContainerItem2'
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype=u'application/x-tar')
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = set(['example1.txt'])
        item.content.put_member('example1.txt', filecontent, content_length, expected_members=members)
        filecontent = 'AAAABBBB'
        content_length = len(filecontent)
        item.content.put_member('example1.txt', filecontent, content_length, expected_members=members)

        item = Item.create(item_name, contenttype=u'application/x-tar')
        assert item.content.get_member('example1.txt').read() == filecontent

class TestZipMixin(object):
    """ Test for zip-like items """

    def test_put_member(self):
        item_name = u'Zip_file'
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype='application/zip')
        filecontent = 'test_contents'
        content_length = len(filecontent)
        members = set(['example1.txt', 'example2.txt'])
        with pytest.raises(NotImplementedError):
            item.content.put_member('example1.txt', filecontent, content_length, expected_members=members)

class TestTransformableBitmapImage(object):

    def test__transform(self):
        item_name = u'image_Item'
        item = Item.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item = Item.create(item_name)
        try:
            from PIL import Image as PILImage
            with pytest.raises(ValueError):
                result = TransformableBitmapImage._transform(item.content, 'text/plain')
        except ImportError:
            result = TransformableBitmapImage._transform(item.content, contenttype)
            assert result == (u'image/jpeg', '')

    def test__render_data_diff(self):
        item_name = u'image_Item'
        item = Item.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        try:
            from PIL import Image as PILImage
            result = Markup(TransformableBitmapImage._render_data_diff(item1.content, item.rev, item1.rev))
            # On Werkzeug 0.8.2+, urls with '+' are automatically encoded to '%2B'
            # The assert statement works with both older and newer versions of Werkzeug
            # Probably not an intentional change on the werkzeug side, see issue:
            # https://github.com/mitsuhiko/werkzeug/issues/146
            assert str(result).startswith('<img src="/+diffraw/image_Item?rev') or \
                    str(result).startswith('<img src="/%2Bdiffraw/image_Item?rev')
        except ImportError:
            # no PIL
            pass

    def test__render_data_diff_text(self):
        item_name = u'image_Item'
        item = Item.create(item_name)
        contenttype = u'image/jpeg'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        data = 'test_data'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Item.create(item_name)
        try:
            from PIL import Image as PILImage
            result = TransformableBitmapImage._render_data_diff_text(item1.content, item1.rev, item2.rev)
            expected = u'The items have different data.'
            assert result == expected
        except ImportError:
            pass

class TestText(object):

    def test_data_conversion(self):
        item_name = u'Text_Item'
        item = Item.create(item_name, ITEMTYPE_DEFAULT, u'text/plain')
        test_text = u'This \n is \n a \n Test'
        # test for data_internal_to_form
        result = Text.data_internal_to_form(item.content, test_text)
        expected = u'This \r\n is \r\n a \r\n Test'
        assert result == expected
        # test for data_form_to_internal
        test_form = u'This \r\n is \r\n a \r\n Test'
        result = Text.data_form_to_internal(item.content, test_text)
        expected = test_text
        assert result == expected
        # test for data_internal_to_storage
        result = Text.data_internal_to_storage(item.content, test_text)
        expected = 'This \r\n is \r\n a \r\n Test'
        assert result == expected
        # test for data_storage_to_internal
        data_storage = 'This \r\n is \r\n a \r\n Test'
        result = Text.data_storage_to_internal(item.content, data_storage)
        expected = test_text
        assert result == expected

    def test__render_data_diff(self):
        item_name = u'Html_Item'
        empty_html = u'<span></span>'
        html = u'<span>\ud55c</span>'
        meta = {CONTENTTYPE: u'text/html;charset=utf-8'}
        item = Item.create(item_name)
        item._save(meta, empty_html)
        item = Item.create(item_name)
        # Unicode test, html escaping
        rev1 = update_item(item_name, meta, html)
        rev2 = update_item(item_name, {}, u'     ')
        result = Text._render_data_diff(item.content, rev1, rev2)
        assert escape(html) in result
        # Unicode test, whitespace
        rev1 = update_item(item_name, {}, u'\n\n')
        rev2 = update_item(item_name, {}, u'\n     \n')
        result = Text._render_data_diff(item.content, rev1, rev2)
        assert '<span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>' in result
        # If fairly similar diffs are correctly spanned or not, also check indent
        rev1 = update_item(item_name, {}, u'One Two Three Four\nSix\n\ud55c')
        rev2 = update_item(item_name, {}, u'Two Three Seven Four\nSix\n\ud55c')
        result = Text._render_data_diff(item.content, rev1, rev2)
        assert '<span>One </span>Two Three Four' in result
        assert 'Two Three <span>Seven </span>Four' in result
        # Check for diff_html.diff return types
        assert reduce(lambda x, y: x and y, [isinstance(i[1], unicode) and isinstance(i[3], unicode) for i in diff_html.diff(u'One Two Three Four\nSix\n', u'Two Three Seven Four\nSix Seven\n')], True)

    def test__render_data_diff_text(self):
        item_name = u'Text_Item'
        item = Item.create(item_name)
        contenttype = u'text/plain'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        data = 'test_data'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Item.create(item_name)
        result = Text._render_data_diff_text(item1.content, item1.rev, item2.rev)
        expected = u'- \n+ test_data'
        assert result == expected
        assert item2.content.data == ''

    def test__render_data_highlight(self):
        item_name = u'Text_Item'
        item = Item.create(item_name)
        contenttype = u'text/plain'
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        data = 'test_data\nnext line'
        comment = u'next revision'
        item1._save(meta, data, comment=comment)
        item2 = Item.create(item_name)
        result = Text._render_data_highlight(item2.content)
        assert u'<pre class="highlight">test_data\n' in result
        assert item2.content.data == ''

coverage_modules = ['MoinMoin.items.content']
