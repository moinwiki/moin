# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# Copyright: 2023 MoinMoin Project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for macros.Date
"""

import time

import pytest
from flask import g as flaskg

from moin.macros.Date import MacroDateTimeBase, Macro
from moin.utils import utcfromtimestamp
from moin.utils.show_time import format_date_time, format_date


class TestMacroDateTimeBase:
    def test_parse_time(self):
        MacroDateTimeBase_obj = MacroDateTimeBase()
        test_time_args = "2023-08-07T11:11:11+0533"
        ts = MacroDateTimeBase_obj.parse_time(test_time_args)
        expected = 1691386691.0
        assert ts == expected

        result = format_date_time(utcfromtimestamp(ts))
        expected = "2023-08-07 05:38:11z"
        assert result == expected

        flaskg.user.valid = True  # show_time creates ISO 8601 dates if user is not logged in
        result = format_date_time(utcfromtimestamp(ts))
        expected = ["Aug 7, 2023, 5:38:11\u202fAM", "Aug 7, 2023, 5:38:11 AM"]  # TODO: remove 2nd entry later
        assert result in expected

        with pytest.raises(ValueError):
            # things after next 10,000 years can't be predicted
            MacroDateTimeBase_obj.parse_time("12011-08-07T11:11:11")


class TestMacro:
    def test_macro(self):
        flaskg.user.valid = True  # show_time creates ISO 8601 dates if user is not logged in
        flaskg.user.timezone = "GMT"
        flaskg.user.locale = "en"
        flaskg.user.iso_8601 = False

        macro_obj = Macro()
        # when arguments is None
        result = macro_obj.macro("content", None, "page_url", "alternative")
        test_time = time.time()
        test_time = format_date(utcfromtimestamp(test_time))
        assert result == test_time

        arguments = ["2023-08-07T11:11:11+0533", "argument2"]
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        expected = "Aug 7, 2023"
        assert result == expected

        flaskg.user.timezone = "UTC"
        flaskg.user.iso_8601 = True
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        expected = "2023-08-07z"
        assert result == expected

        flaskg.user.timezone = "America/Phoenix"
        result = macro_obj.macro("content", arguments, "page_url", "alternative")
        expected = "2023-08-07"
        assert result == expected
