# Copyright: 2012 MoinMoin:PavelSviderski
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.forms Tests
"""

import datetime
from calendar import timegm

from MoinMoin.forms import DateTimeUNIX


def test_datetimeunix():
    dt = datetime.datetime(2012, 12, 21, 23, 45, 59)
    timestamp = timegm(dt.timetuple())
    dt_u = u'2012-12-21 23:45:59'

    d = DateTimeUNIX(timestamp)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestamp = 999999999999
    d = DateTimeUNIX(incorrect_timestamp)
    assert d.value is None
    assert d.u == unicode(incorrect_timestamp)

    d = DateTimeUNIX(dt)
    assert d.value == timestamp
    assert d.u == dt_u

    # parse time string
    d = DateTimeUNIX(dt_u)
    assert d.value == timestamp
    assert d.u == dt_u

    incorrect_timestring = u'2012-10-30'
    d = DateTimeUNIX(incorrect_timestring)
    assert d.value is None
    assert d.u == incorrect_timestring

    d = DateTimeUNIX(None)
    assert d.value is None
    assert d.u == u''
