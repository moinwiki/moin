# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# Copyright: 2023 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.DateTime
"""

import time

from flask import g as flaskg

from moin.macros.DateTime import Macro
from moin.utils import utcfromtimestamp
from moin.utils.show_time import format_date_time


def test_Macro():
    """Test: DateTime.Macro"""
    flaskg.user.valid = True  # show_time creates ISO 8601 dates if user is not logged in
    macro_obj = Macro()
    # when arguments is None
    result = macro_obj.macro("content", None, "page_url", "alternative")
    # get the current time
    test_time = time.time()
    test_times = [test_time, test_time - 1]  # in case our call to time.time happened just after the second rolled over
    test_times = [format_date_time(utcfromtimestamp(t)) for t in test_times]
    assert result in test_times

    arguments = ["2023-08-07T11:11:11", "argument2"]
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    expected = ["Aug 7, 2023, 11:11:11\u202fAM", "Aug 7, 2023, 11:11:11 AM"]  # TODO: remove 2nd entry later
    assert result in expected

    flaskg.user.valid = False
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    expected = "2023-08-07 11:11:11z"
    assert result == expected

    arguments = ["incorrect_argument"]
    result = macro_obj.macro("content", arguments, "page_url", "alternative")
    attr = list(result.attrib.values())
    # expecting error message with class of 'error nowiki'
    assert "error" in attr[0]

    # the following are different ways to specify the same moment
    expected = "2019-10-07 18:30:00z"
    arguments = [
        "2019-10-07T18:30:00Z" "2019-10-07T22:30:00+0400",
        "2019-10-07 11:30:00-0700",  # ascii hyphen-minus
        "2019-10-07T15:00:00-0330",
        "2019-10-07 11:30:00\u22120700",  # unicode minus \u2212
        "2019-10-07T15:00:00\u22120330",
    ]
    for arg in arguments:
        result = macro_obj.macro("content", (arg,), "page_url", "alternative")
        assert result == expected
