# Copyright: 2022 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.macros.ItemList Tests
"""

from moin.items import Item
from moin.constants.keys import CONTENTTYPE, ITEMTYPE, REV_NUMBER
from moin._tests import wikiconfig, update_item

meta = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ITEMTYPE: "default", REV_NUMBER: 1}


class TestItemListMacro:
    """
    call ItemList macro and test ...
    """

    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_ItemListFullPath(self):
        update_item("item01", meta, "some-content")
        update_item("item02", meta, "some-content")
        update_item("other", meta, "some-content")

        update_item("TestItemList", meta, '<<ItemList(item="",startswith="item",display="FullPath")>>')

        rendered = Item.create("TestItemList").content._render_data()
        assert 'a href="/item01">item01' in rendered
        assert 'a href="/item02">item02' in rendered
        assert "other" not in rendered

    def test_ItemListChildPath(self):
        update_item("item01", meta, "some-content")
        update_item("item02", meta, "some-content")
        update_item("other", meta, "some-content")

        update_item("TestItemList", meta, '<<ItemList(item="",startswith="item",display="ChildPath")>>')

        rendered = Item.create("TestItemList").content._render_data()
        assert 'a href="/item01">item01' in rendered
        assert 'a href="/item02">item02' in rendered
        assert "other" not in rendered

    def test_ItemListParent(self):
        update_item("parent", meta, "some-content")
        update_item("parent/item01", meta, "some-content")
        update_item("parent/item02", meta, "some-content")
        update_item("parent/other01", meta, "some-content")
        update_item("item03", meta, "some-content")
        update_item("other02", meta, "some-content")

        update_item("TestItemList01", meta, '<<ItemList(item="",startswith="parent/item")>>')

        rendered = Item.create("TestItemList01").content._render_data()
        assert 'a href="/parent/item01">parent/item01' in rendered
        assert 'a href="/parent/item02">parent/item02' in rendered
        assert "other" not in rendered

        update_item("TestItemList02", meta, '<<ItemList(item="parent",startswith="item")>>')

        rendered = Item.create("TestItemList02").content._render_data()
        assert "other02" not in rendered
        assert "item03" not in rendered

    def test_ItemListRegex(self):
        update_item("parent", meta, "some-content")
        update_item("parent/item01", meta, "some-content")
        update_item("parent/otheritem", meta, "some-content")
        update_item("item02", meta, "some-content")
        update_item("other02", meta, "some-content")

        update_item("TestItemList03", meta, '<<ItemList(item="",regex="item")>>')

        rendered = Item.create("TestItemList03").content._render_data()
        assert 'a href="/parent/item01">parent/item01' in rendered
        assert 'a href="/parent/otheritem">parent/otheritem' in rendered
        assert 'a href="/item02">item02' in rendered
        assert "other02" not in rendered

        update_item("TestItemList04", meta, '<<ItemList(item="parent",regex="^parent/item")>>')

        rendered = Item.create("TestItemList04").content._render_data()
        assert 'a href="/parent/item01">parent/item01' in rendered
        assert "item02" not in rendered
        assert "other" not in rendered
