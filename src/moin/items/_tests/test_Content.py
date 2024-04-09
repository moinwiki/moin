# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2009 MoinMoin:ThomasWaldmann
# TODO: Split tests for Content subclasses after the subclasses themselves are
# split

"""
    MoinMoin - moin.items.content Tests
"""

import pytest
from io import BytesIO

from markupsafe import Markup, escape

from moin.utils import diff_html

from moin._tests import update_item
from moin.items import Item
from moin.items.content import Content, Binary, Text, Image, TransformableBitmapImage
from moin.constants.keys import CONTENTTYPE, TAGS, TEMPLATE
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.utils.interwiki import split_fqname
from functools import reduce


class TestContent:
    """Test for arbitrary content"""

    def testClassFinder(self):
        for contenttype, ExpectedClass in [
            ("application/x-foobar", Binary),
            ("text/plain", Text),
            ("text/plain;charset=utf-8", Text),
            ("image/tiff", Image),
            ("image/png", TransformableBitmapImage),
        ]:
            content = Content.create(contenttype)
            assert isinstance(content, ExpectedClass)

    def test_get_templates(self):
        item_name1 = "Template_Item1"
        item1 = Item.create(item_name1)
        contenttype1 = "text/plain;charset=utf-8"
        meta = {CONTENTTYPE: contenttype1, TAGS: [TEMPLATE]}
        item1._save(meta)
        item1 = Item.create(item_name1)

        item_name2 = "Template_Item2"
        item2 = Item.create(item_name2)
        contenttype1 = "text/plain;charset=utf-8"
        meta = {CONTENTTYPE: contenttype1, TAGS: [TEMPLATE]}
        item2._save(meta)
        item2 = Item.create(item_name2)

        item_name3 = "Template_Item3"
        item3 = Item.create(item_name3)
        contenttype2 = "image/png"
        meta = {CONTENTTYPE: contenttype2, TAGS: [TEMPLATE]}
        item3._save(meta)
        item3 = Item.create(item_name3)
        # two items of same content type
        result1 = item1.content.get_templates(contenttype1)
        assert result1 == [item_name1, item_name2]
        # third of different content type
        result2 = item1.content.get_templates(contenttype2)
        assert result2 == [item_name3]


class TestTarItems:
    """
    tests for the container items
    """

    def testCreateContainerRevision(self):
        """
        creates a container and tests the content saved to the container
        """
        item_name = "ContainerItem1"
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype="application/x-tar")
        filecontent = b"abcdefghij"
        content_length = len(filecontent)
        members = {"example1.txt", "example2.txt"}
        item.content.put_member("example1.txt", filecontent, content_length, expected_members=members)
        item.content.put_member("example2.txt", filecontent, content_length, expected_members=members)

        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype="application/x-tar")
        tf_names = set(item.content.list_members())
        assert tf_names == members
        assert item.content.get_member("example1.txt").read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        item_name = "ContainerItem2"
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype="application/x-tar")
        filecontent = b"abcdefghij"
        content_length = len(filecontent)
        members = {"example1.txt"}
        item.content.put_member("example1.txt", filecontent, content_length, expected_members=members)
        filecontent = b"AAAABBBB"
        content_length = len(filecontent)
        item.content.put_member("example1.txt", filecontent, content_length, expected_members=members)

        item = Item.create(item_name, contenttype="application/x-tar")
        assert item.content.get_member("example1.txt").read() == filecontent


class TestZipMixin:
    """Test for zip-like items"""

    def test_put_member(self):
        item_name = "Zip_file"
        item = Item.create(item_name, itemtype=ITEMTYPE_DEFAULT, contenttype="application/zip")
        filecontent = "test_contents"
        content_length = len(filecontent)
        members = {"example1.txt", "example2.txt"}
        with pytest.raises(NotImplementedError):
            item.content.put_member("example1.txt", filecontent, content_length, expected_members=members)


class TestTransformableBitmapImage:

    def test__transform(self):
        item_name = "image_Item"
        item = Item.create(item_name)
        contenttype = "image/jpeg"
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item = Item.create(item_name)
        try:
            from PIL import Image as PILImage  # noqa

            with pytest.raises(ValueError):
                result = TransformableBitmapImage._transform(item.content, "text/plain")
        except ImportError:
            result = TransformableBitmapImage._transform(item.content, contenttype)
            assert result == ("image/jpeg", b"")

    def test__render_data_diff(self):
        item_name = "image_Item"
        item = Item.create(item_name)
        contenttype = "image/jpeg"
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        try:
            from PIL import Image as PILImage  # noqa

            result = Markup(TransformableBitmapImage._render_data_diff(item1.content, item.rev, item1.rev))
            # On Werkzeug 0.8.2+, urls with '+' are automatically encoded to '%2B'
            # The assert statement works with both older and newer versions of Werkzeug
            # Probably not an intentional change on the werkzeug side, see issue:
            # https://github.com/mitsuhiko/werkzeug/issues/146
            assert str(result).startswith('<img src="/+diffraw/image_Item?rev') or str(result).startswith(
                '<img src="/%2Bdiffraw/image_Item?rev'
            )
        except ImportError:
            # no PIL
            pass

    def test__render_data_diff_text(self):
        item_name = "image_Item"
        item = Item.create(item_name)
        contenttype = "image/jpeg"
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        data = b"test_data"
        comment = "next revision"
        item1._save(meta, data, comment=comment)
        item2 = Item.create(item_name)
        try:
            from PIL import Image as PILImage  # noqa

            result = TransformableBitmapImage._render_data_diff_text(item1.content, item1.rev, item2.rev)
            expected = "The items have different data."
            assert result == expected
        except ImportError:
            pass


class TestText:

    def test_data_conversion(self):
        item_name = "Text_Item"
        item = Item.create(item_name, ITEMTYPE_DEFAULT, "text/plain;charset=utf-8")
        test_text = "This \n is \n a \n Test"
        # test for data_internal_to_form
        result = Text.data_internal_to_form(item.content, test_text)
        expected = "This \r\n is \r\n a \r\n Test"
        assert result == expected
        # test for data_form_to_internal
        test_form = "This \r\n is \r\n a \r\n Test"
        result = Text.data_form_to_internal(item.content, test_form)
        expected = test_text
        assert result == expected
        # test for data_internal_to_storage
        result = Text.data_internal_to_storage(item.content, test_text)
        expected = b"This \r\n is \r\n a \r\n Test"
        assert result == expected
        # test for data_storage_to_internal
        data_storage = b"This \r\n is \r\n a \r\n Test"
        result = Text.data_storage_to_internal(item.content, data_storage)
        expected = test_text
        assert result == expected

    def test__render_data_diff(self):
        item_name = "Html_Item"
        fqname = split_fqname(item_name)
        empty_html = "<span></span>"
        html = "<span>\ud55c</span>"
        meta = {CONTENTTYPE: "text/html;charset=utf-8"}
        item = Item.create(item_name)
        item._save(meta, empty_html)
        item = Item.create(item_name)
        # Unicode test, html escaping
        rev1 = update_item(item_name, meta, html)
        rev2 = update_item(item_name, {}, "     ")
        result = Text._render_data_diff(item.content, rev1, rev2, fqname=fqname)
        assert escape(html) in result
        # Unicode test, whitespace
        rev1 = update_item(item_name, {}, "\n\n")
        rev2 = update_item(item_name, {}, "\n     \n")
        result = Text._render_data_diff(item.content, rev1, rev2, fqname=fqname)
        assert "<span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>" in result
        # If fairly similar diffs are correctly spanned or not, also check indent
        rev1 = update_item(item_name, {}, "One Two Three Four\nSix\n\ud55c")
        rev2 = update_item(item_name, {}, "Two Three Seven Four\nSix\n\ud55c")
        result = Text._render_data_diff(item.content, rev1, rev2, fqname=fqname)
        assert "<span>One </span>Two Three Four" in result
        assert "Two Three <span>Seven </span>Four" in result
        # Check for diff_html.diff return types
        assert reduce(
            lambda x, y: x and y,
            [
                isinstance(i[1], str) and isinstance(i[3], str)
                for i in diff_html.diff("One Two Three Four\nSix\n", "Two Three Seven Four\nSix Seven\n")
            ],
            True,
        )

    def test__render_data_diff_text(self):
        item_name = "Text_Item"
        item = Item.create(item_name)
        contenttype = "text/plain;charset=utf-8"
        meta = {CONTENTTYPE: contenttype}
        data1 = b"old_data"
        item._save(meta, data1)
        item1 = Item.create(item_name)
        data2 = b"new_data"
        comment = "next revision"
        item1._save(meta, data2, comment=comment)
        item2 = Item.create(item_name)
        result = Text._render_data_diff_text(item1.content, item1.rev, item2.rev)
        expected = "- old_data\n+ new_data"
        assert result == expected
        assert item2.content.data == b""

    def test__render_data_highlight(self):
        item_name = "Text_Item"
        item = Item.create(item_name)
        contenttype = "text/plain;charset=utf-8"
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item1 = Item.create(item_name)
        data = "test_data\nnext line"
        comment = "next revision"
        item1._save(meta, data, comment=comment)
        item2 = Item.create(item_name)
        result = Text._render_data_highlight(item2.content)
        assert '<pre class="highlight">test_data\n' in result
        assert item2.content.data == b""

    def test__get_data_diff_text(self):
        item_name = "Text_Item"
        item = Item.create(item_name)
        contenttypes = dict(
            texttypes=["text/plain;charset=utf-8", "text/x-markdown;charset=utf-8"],
            othertypes=["image/png", "audio/wave", "video/ogg", "application/x-svgdraw", "application/octet-stream"],
        )
        for key in contenttypes:
            for contenttype in contenttypes[key]:
                meta = {CONTENTTYPE: contenttype}
                item._save(meta)
                item_ = Item.create(item_name)
                oldfile = BytesIO(b"x")
                newfile = BytesIO(b"xx")
                difflines = item_.content._get_data_diff_text(oldfile, newfile)
                if key == "texttypes":
                    assert difflines == ["- x", "+ xx"]
                else:
                    assert difflines == []

    def test__get_data_diff_html(self):
        item_name = "Test_Item"
        item = Item.create(item_name)
        contenttype = "text/plain;charset=utf-8"
        meta = {CONTENTTYPE: contenttype}
        item._save(meta)
        item_ = Item.create(item_name)
        oldfile = BytesIO(b"")
        newfile = BytesIO(b"x")
        difflines = item_.content._get_data_diff_html(oldfile, newfile)
        assert difflines == [(1, Markup(""), 1, Markup("<span>x</span>"))]


coverage_modules = ["moin.items.content"]
