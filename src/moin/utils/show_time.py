# Copyright: 2019 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Provide a consistent way of formatting times and durations.

For formatted times, all date-times passed into this module should be GMT Zulu times
    * if logged-in user or wikiconfig has specified a time zone,
        use it to convert GMT times to local times.
    * if logged-in user or wikiconfig has a default/preferred time format,
        use it to format output strings.
    * default output will use GMT ISO 8601 time formats, without the T and ignoring
        seconds to save space.
    * formatted Zulu times will have a trailing Z, local times will not
    * in most cases, logged-in users will see local times, casual visitors will see Zulu times

For duration times, seconds will be converted into approximate, minutes, days, weeks, months, years.

TODO: complete the code and convert other modules to use this module.
"""


import time
import datetime
import pytz

from flask import g as flaskg

from moin.constants.keys import TIMEZONE
from moin.i18n import _, L_, N_
from moin import i18n


def duration(seconds):
    """
    Convert seconds into a multiple of an interval (seconds, 10; minutes, 5; ), return as a tuple
    suitable for inserting into a translated phrase.
    """
    seconds = int(abs(seconds))
    if seconds < 90:
        return _("seconds"), seconds
    if seconds < 5400:  # 1.5 hours
        return _("minutes"), (seconds+30)//60
    if seconds < 129600:  # 36 hours
        return _("hours"), (seconds+1800)//3600
    if seconds < 864000:  # 10 days
        return _("days"), (seconds+43200)//86400
    if seconds < 4838400:  # 8 weeks
        return _("weeks"), (seconds+302400)//604800
    if seconds < 63072000:  # 24 months
        return _("months"), (seconds+1296000)//2592000
    return _("years"), (seconds+15768000)//31536000


def format_date_time(utc_dt=None):
    """Return current or passed (dt) time in user's preferred format or default to moin-style ISO 8601."""
    if utc_dt is None:
        utc_dt = datetime.datetime.utcnow()
    user_tz = i18n.get_timezone()
    if user_tz:
        tz = pytz.timezone(user_tz)
        fmt = '%Y-%m-%d %H:%M'
    else:
        tz = pytz.utc
        fmt = '%Y-%m-%d %H:%MZ'
    loc_dt = tz.localize(utc_dt)
    dt = loc_dt.strftime(fmt)
    print '%s' % dt
    return dt
