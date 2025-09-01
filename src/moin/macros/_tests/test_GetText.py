# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.GetText.
"""

from moin.converters._args import Arguments
from moin.macros.GetText import Macro


def test_Macro():
    """Test Macro.macro."""
    macro_obj = Macro()
    arguments = Arguments(["test_argument1 test_argument2"])
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    expected = "test_argument1 test_argument2"
    assert result == expected
