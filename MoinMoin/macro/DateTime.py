# Copyright: 2008-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin DateTime macro - outputs the date and time for some specific point in time,
    adapted to the TZ settings of the user viewing the content.
"""


from flask import flaskg
from flaskext.babel import format_datetime

from MoinMoin.macro.Date import MacroDateTimeBase

class Macro(MacroDateTimeBase):
    def macro(self, stamp=None):
        tm = self.parse_time(stamp)
        return format_datetime(tm)

