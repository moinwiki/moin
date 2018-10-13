# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.Anchor
"""

import pytest

from moin.macros.Anchor import Macro


def test_Macro():
    macro_obj = Macro()
    with pytest.raises(ValueError):
        macro_obj.macro('content', None, 'page_url', 'alternative')

    arguments = [('test_argument1', 'test_argument2'), 'test_argument3']
    result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
    test_anchor = result.attrib.values()
    # test_anchor[0] since it returns a list
    assert test_anchor[0] == arguments[0]
