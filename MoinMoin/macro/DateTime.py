# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin DateTime macro - outputs the date and time for some specific point in time,
adapted to the TZ settings of the user viewing the content.
"""

import time
from datetime import datetime

from flask import g as flaskg
from flask.ext.babel import format_datetime

from MoinMoin.macro.Date import MacroDateTimeBase

class Macro(MacroDateTimeBase):
    def macro(self, content, arguments, page_url, alternative):
        if arguments is None:
            tm = time.time() # always UTC
        else:
            stamp = arguments[0]
            tm = self.parse_time(stamp)
        return format_datetime(datetime.utcfromtimestamp(tm))
