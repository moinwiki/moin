# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.GetVal
"""

import pytest
from flask import g as flaskg

from moin.macros.GetVal import Macro
from moin.constants.keys import WIKIDICT
from moin._tests import become_trusted, update_item


class TestMacro:
    @pytest.fixture
    def test_dict(self):
        become_trusted()
        wikidict = {"One": "1", "Two": "2"}
        update_item("TestDict", {WIKIDICT: wikidict}, "This is a dict item.")

        return "TestDict"

    def test_Macro(self, test_dict):
        macro_obj = Macro()
        arguments = [test_dict]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        attr = list(result.attrib.values())
        # expecting error message with class of 'error nowiki'
        assert "error" in attr[0]

        if not flaskg.user.may.read(arguments[0]):
            with pytest.raises(ValueError):
                macro_obj.macro("content", arguments, "page_url", "alternative")

        arguments = ["TestDict, One"]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        assert result == "1"

        # change the value of second element
        arguments = ["TestDict, Two"]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        assert result == "2"
