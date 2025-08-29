# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.GetVal.
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
        """Test Macro.macro."""
        macro_obj = Macro()
        arguments = [test_dict]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        attr = list(result.attrib.values())
        # Expect an error message with class 'error nowiki'
        assert "error" in attr[0]

        if not flaskg.user.may.read(arguments[0]):
            with pytest.raises(ValueError):
                macro_obj.macro("content", arguments, "page_url", "alternative")

        arguments = ["TestDict, One"]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        assert result == "1"

        # Change the value of the second element
        arguments = ["TestDict, Two"]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        assert result == "2"
