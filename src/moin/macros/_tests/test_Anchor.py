# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.Anchor
"""

from moin.macros.Anchor import Macro
from moin.utils.tree import moin_page


def test_Macro():
    macro_obj = Macro()
    arguments = ["my_anchor"]
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    test_anchor = list(result.attrib.values())
    # test_anchor[0] since it returns a list
    assert test_anchor[0] == arguments[0]
    assert result.attrib[moin_page.id] == "my_anchor"

    arguments = []
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    test_anchor = list(result.attrib.values())
    # expecting error message with class of 'error nowiki'
    assert "error" in test_anchor[0]
