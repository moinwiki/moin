# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.DateTime
"""

import time
from datetime import datetime

from flask import g as flaskg

import pytest

from moin.macros.DateTime import Macro
from moin.utils.show_time import format_date_time


def test_Macro():
    """Test: DateTime.Macro """
    flaskg.user.valid = True  # show_time creates ISO 8601 dates if user is not logged in
    macro_obj = Macro()
    # when arguments is None
    result = macro_obj.macro('content', None, 'page_url', 'alternative')
    # get the current time
    test_time = time.time()
    test_time = format_date_time(datetime.utcfromtimestamp(test_time))
    assert test_time == result

    arguments = ['2011-08-07T11:11:11', 'argument2']
    result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
    expected = 'Aug 7, 2011, 11:11:11 AM'  # comma after year was added in recent CLDR
    assert result == expected

    flaskg.user.valid = False
    result = macro_obj.macro('content', arguments, 'page_url', 'alternative')
    expected = '2011-08-07 11:11:11z'
    assert result == expected

    arguments = ['incorrect_argument']
    with pytest.raises(ValueError):
        macro_obj.macro('content', arguments, 'page_url', 'alternative')

    # the following are different ways to specify the same moment
    expected = '2019-10-07 18:30:00z'
    arguments = ['2019-10-07T18:30:00Z'
                 '2019-10-07T22:30:00+0400',
                 '2019-10-07 11:30:00-0700',  # ascii hyphen-minus
                 '2019-10-07T15:00:00-0330',
                 '2019-10-07 11:30:00\u22120700',  # unicode minus \u2212
                 '2019-10-07T15:00:00\u22120330', ]
    for arg in arguments:
        result = macro_obj.macro('content', (arg, ), 'page_url', 'alternative')
        assert result == expected
