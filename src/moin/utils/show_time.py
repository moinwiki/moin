# Copyright: 2019 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import pytz

from flask import g as flaskg
import flask_babel

from moin.i18n import _
from moin import i18n
from moin.utils import utcfromtimestamp, utcnow


def duration(seconds):
    """
    Return a duration tuple (interval, number) suitable for inserting into a translated phrase.

        * (_('seconds'), 10)
        * (_('minutes'), 5)
    """
    seconds = int(abs(seconds))
    if seconds < 90:
        return _("seconds"), seconds
    if seconds < 5400:  # 1.5 hours
        return _("minutes"), (seconds + 30) // 60
    if seconds < 129600:  # 36 hours
        return _("hours"), (seconds + 1800) // 3600
    if seconds < 864000:  # 10 days
        return _("days"), (seconds + 43200) // 86400
    if seconds < 4838400:  # 8 weeks
        return _("weeks"), (seconds + 302400) // 604800
    if seconds < 63072000:  # 24 months
        return _("months"), (seconds + 1296000) // 2592000
    return _("years"), (seconds + 15768000) // 31536000


def format_date_time(utc_dt=None, fmt="yyyy-MM-dd HH:mm:ss", interval="datetime"):
    """
    Add an ISO 8601 alternative to babel's date/time formatting.

    Visitors who are not logged-in see ISO 8601 formatted dates and times with
    a "z" suffix indicating the date/time is a UTC Zulu time.

    Logged in users who have selected the ISO 8601 option in usersettings and
    have set their time zone to UTC in usersettings see date/times with a "z" suffix.
    Users with a time zone other than UTC see local date/times in ISO 8601 format
    without the "z" suffix.

    All other logged-in users will see the usual babel date/time formats based upon
    their time zone and locale.

    See https://babel.pocoo.org/en/latest/dates.html#date-fields for babel format syntax.
    """
    if utc_dt is None:
        utc_dt = utcnow()
    elif isinstance(utc_dt, (float, int)):
        utc_dt = utcfromtimestamp(utc_dt)

    if not flaskg.user.valid:
        # users who are not logged-in get moin version of ISO 8601: 2019-07-15 07:08:09z
        return flask_babel.format_datetime(utc_dt, fmt) + "z"

    if flaskg.user.iso_8601:
        suffix = ""
        user_tz = i18n.get_timezone()
        if user_tz:
            if pytz.timezone(user_tz) == pytz.utc:
                suffix = "z"
        return flask_babel.format_datetime(utc_dt, fmt) + suffix

    if interval == "date":
        return flask_babel.format_date(utc_dt)
    elif interval == "time":
        return flask_babel.format_time(utc_dt)
    return flask_babel.format_datetime(utc_dt)


def format_date(utc_dt=None, fmt="yyyy-MM-dd", interval="date"):
    return format_date_time(utc_dt=utc_dt, fmt=fmt, interval=interval)


def format_time(utc_dt=None, fmt="HH:mm:ss", interval="time"):
    return format_date_time(utc_dt=utc_dt, fmt=fmt, interval=interval)
