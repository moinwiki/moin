# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macro.DateTime
"""

import time
from datetime import datetime

import pytest

from MoinMoin.macro.DateTime import *


def test_Macro():
    """Test: DateTime.Macro """

    macro_obj = Macro()
    # when arguments is None
    result = macro_obj.macro('content', None, 'page_url', 'alternative')
    # get the current time
    test_time = time.time()
    test_time = format_datetime(datetime.utcfromtimestamp(test_time))
    assert test_time == result

    arguments = ['2011-08-07T11:11:11', 'argument2']
    result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
    expected = u'Aug 7, 2011, 11:11:11 AM'  # comma after year was added in recent CLDR
    assert result == expected

    arguments = ['incorrect_argument']
    with pytest.raises(ValueError):
        macro_obj.macro('content', arguments, 'page_url', 'alternative')
