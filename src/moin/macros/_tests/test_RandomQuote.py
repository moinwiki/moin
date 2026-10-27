# Copyright: 2022 MoinMoin
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.RandomQuote.
"""

import pytest

from emeraldtree.tree import tostring, Element

from moin.macros.RandomQuote import Macro
from moin._tests import update_item
from moin.utils.iri import Iri
from moin.constants.keys import CONTENTTYPE, ITEMTYPE, REV_NUMBER
from moin.utils.tree import html, moin_page

meta = {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ITEMTYPE: "default", REV_NUMBER: 1}
page_url = Iri(scheme="wiki", authority="", path="/TestPage")


def is_error_result(res):
    return res is not None and isinstance(res, Element) and res.tag == html.div and "error" in res.get(html.class_, "")


@pytest.mark.usefixtures("_req_ctx")
class TestRandomQuote:

    def test_default_item_not_exists(self):
        macro_object = Macro()
        argument = []
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert is_error_result(res)

    def test_default_item_exists(self):
        macro_object = Macro()
        argument = []
        update_item("FortuneCookies", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res is not None
        assert not is_error_result(res)
        assert isinstance(res, Element)
        assert res.tag == moin_page.p
        assert len(res)
        assert b"quote" in tostring(res)

    def test_non_exits_item(self):
        macro_object = Macro()
        argument = ["Random page"]
        update_item("FortuneCookies", meta, data="* First quote\n* Second quote")
        update_item("item1", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert is_error_result(res)

    def test_no_quotes_in_item(self):
        macro_object = Macro()
        argument = []
        update_item("FortuneCookies", meta, data="First quote\n Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert is_error_result(res)
        assert b"No quotes found in" in tostring(res)

    def test_single_quote_in_item(self):
        macro_object = Macro()
        argument = ["item1"]
        update_item("item1", meta, data="First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res is not None
        assert not is_error_result(res)

    def test_item_name_with_surrounding_quotes(self):
        macro_object = Macro()
        argument = ["'item1'"]
        update_item("item1", meta, data="* First quote\n* Second quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res is not None
        assert not is_error_result(res)

    def test_invalid_item_name(self):
        macro_object = Macro()
        argument = ["/InvalidItem"]
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert is_error_result(res)

    def test_mixed_quotes_in_item(self):
        macro_object = Macro()
        argument = ["item1"]
        update_item("item1", meta, data="First quote\n* Second quote\n Third quote")
        res = macro_object.macro("content", argument, page_url, "alternative")
        assert res is not None
        assert not is_error_result(res)
