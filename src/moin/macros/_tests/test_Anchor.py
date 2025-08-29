# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.Anchor.
"""

from moin.macros.Anchor import Macro
from moin.utils.tree import moin_page


def test_Macro():
    """Test Macro.macro."""
    macro_obj = Macro()
    arguments = ["my_anchor"]
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    test_anchor = list(result.attrib.values())
    # test_anchor[0] is used because it returns a list.
    assert test_anchor[0] == arguments[0]
    assert result.attrib[moin_page.id] == "my_anchor"

    arguments = []
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    test_anchor = list(result.attrib.values())
    # Expect an error message with class 'error nowiki'.
    assert "error" in test_anchor[0]
