# Copyright: 2019 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - test moin.utils.show_time
"""
from flask import g as flaskg

from moin.utils import show_time


class TestShowTime:

    def test_showTime_duration(self):
        """test somewhat arbitrary duration results"""
        seconds_expected = (
            (25, ("seconds", 25)),
            (89, ("seconds", 89)),
            (91, ("minutes", 2)),
            (5399, ("minutes", 90)),
            (5401, ("hours", 2)),
            (128999, ("hours", 36)),
            (864000, ("weeks", 1)),
            (4838399, ("weeks", 8)),
            (4838401, ("months", 2)),
            (63071999, ("months", 24)),
            (126144000, ("years", 4)),
        )

        for seconds, expected in seconds_expected:
            result = show_time.duration(seconds)
            assert result == expected

    def test_show_time_datetime(self):
        """users who are not logged-in get ISO 8601 Zulu dates"""
        formatted_date = show_time.format_date(utc_dt=0)
        assert formatted_date == "1970-01-01z"
        formatted_time = show_time.format_time(utc_dt=0)
        assert formatted_time == "00:00:00z"
        formatted_date_time = show_time.format_date_time(utc_dt=0)
        assert formatted_date_time == "1970-01-01 00:00:00z"

    def test_show_time_datetime_logged_in_utc(self):
        """users who are logged-in, selected UTC timezone and checked ISO-8601 get ISO 8601 Zulu dates"""
        flaskg.user.valid = True
        flaskg.user.timezone = "UTC"
        flaskg.user.locale = "en"
        flaskg.user.iso_8601 = True
        formatted_date = show_time.format_date(utc_dt=0)
        assert formatted_date == "1970-01-01z"
        formatted_time = show_time.format_time(utc_dt=0)
        assert formatted_time == "00:00:00z"
        formatted_date_time = show_time.format_date_time(utc_dt=0)
        assert formatted_date_time == "1970-01-01 00:00:00z"

    def test_show_time_datetime_logged_in_local(self):
        """users who are logged-in, unchecked ISO-8601 get dates based on locale and timezone"""
        flaskg.user.valid = True
        flaskg.user.locale = "en"
        flaskg.user.iso_8601 = False
        flaskg.user.timezone = "America/Phoenix"
        formatted_date = show_time.format_date(utc_dt=0)
        assert formatted_date == "Dec 31, 1969"
        formatted_time = show_time.format_time(utc_dt=0)
        assert formatted_time in ["5:00:00\u202fPM", "5:00:00 PM"]  # TODO: 2nd string can be removed in future
        formatted_date_time = show_time.format_date_time(utc_dt=0)
        assert formatted_date_time in ["Dec 31, 1969, 5:00:00\u202fPM", "Dec 31, 1969, 5:00:00 PM"]  # TODO: ditto


coverage_modules = ["moin.utils.show_time"]
