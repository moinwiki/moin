# Copyright: 2022 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.RandomQuote.
"""

import pytest
from moin.macros.RandomQuote import Macro
from moin._tests import update_item
from moin.utils.iri import Iri
from moin.constants.keys import CONTENTTYPE, ITEMTYPE, REV_NUMBER
from moin.utils.tree import html

meta = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ITEMTYPE: "default", REV_NUMBER: 1}
page_url = Iri(scheme="wiki", authority="", path="/TestPage")


@pytest.mark.usefixtures("_req_ctx")
class TestRandomQuote:

    def test_default_item_not_exists(self):
        macro_object = Macro()
        argument = []
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag == html.div

    def test_default_item_exists(self):
        macro_object = Macro()
        argument = []
        update_item("FortuneCookies", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res is not None
        assert res.tag != html.div

    def test_non_exits_item(self):
        macro_object = Macro()
        argument = ["Random page"]
        update_item("FortuneCookies", meta, data="* First quote\n* Second quote")
        update_item("item1", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag == html.div

    def test_no_quotes_in_item(self):
        macro_object = Macro()
        argument = []
        update_item("FortuneCookies", meta, data="First quote\n Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag == html.div

    def test_single_quote_in_item(self):
        macro_object = Macro()
        argument = ["item1"]
        update_item("item1", meta, data="First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag != html.div
        assert res is not None

    def test_item_name_with_surrounding_quotes(self):
        macro_object = Macro()
        argument = ["'item1'"]
        update_item("item1", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag != html.div
        assert res is not None

    def test_invalid_item_name(self):
        macro_object = Macro()
        argument = ["/InvalidItem"]
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag == html.div

    def test_mixed_quotes_in_item(self):
        macro_object = Macro()
        argument = ["item1"]
        update_item("item1", meta, data="First quote\n* Second quote\n Third quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res.tag != html.div
        assert res is not None
