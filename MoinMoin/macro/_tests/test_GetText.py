# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macro.GetText
"""

import pytest
from MoinMoin.converter._args import Arguments
from MoinMoin.macro.GetText import *

def test_Macro():
    """ test for Macro.macro """
    macro_obj = Macro()
    arguments = Arguments(['test_argument1', 'test_argument2'])
    result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
    expected = u'test_argument1 test_argument2'
    assert result == expected
