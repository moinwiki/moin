# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros.Verbatim.
"""

from moin.macros.Verbatim import Macro


def test_Macro():
    arguments = ["test text"]
    macro_obj = Macro()
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    assert result == "test text"
