# Copyright: 2022 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.RandomItem.
"""

import pytest

from moin.macros.RandomItem import Macro
from moin.utils.tree import xlink
from moin._tests import update_item
from moin.constants.keys import CONTENTTYPE, ITEMTYPE, REV_NUMBER

meta = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ITEMTYPE: "default", REV_NUMBER: 1}


@pytest.mark.usefixtures("_req_ctx")
class TestRandomItem:

    def test_no_arguments(self):
        macro_object = Macro()
        argument = []
        res = macro_object.macro("content", argument, "page_url", "alternative")
        assert res is None

    def test_one_argument(self):
        macro_object = Macro()
        argument = ["1"]
        res = macro_object.macro("content", argument, "page_url", "alternative")
        assert res is None

    def test_with_one_updated(self):
        update_item("item1", meta, data="Hello world")

        macro_object = Macro()
        argument = ["1"]
        res = macro_object.macro("content", argument, "page_url", "alternative")
        assert len(res) == 1
        assert res[0].attrib[xlink.href] == "wiki:///item1"

    def test_with_update_items(self):
        update_item("item1", meta, data="Hello world")
        update_item("item2", meta, data="Moin Moin Wiki")
        update_item("item3", meta, data="Test file")

        macro_object = Macro()
        argument = ["2"]
        count = 2
        res = macro_object.macro("content", argument, "page_url", "alternative")
        assert len(res) == (2 * count) - 1
        assert res[0].text in ["item1", "item2", "item3"]

    def test_multiple_items(self):
        macro_object = Macro()
        argument = ["10"]
        count = 5

        for i in range(count):
            update_item(f"item{i}", meta, data=f"Moin Moin Wiki {i}")

        res = macro_object.macro("content", argument, "page_url", "alternative")
        assert len(res) == (2 * count) - 1
