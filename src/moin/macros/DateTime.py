# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin DateTime macro - outputs the date and time for some specific point in time,
adapted to the TZ settings of the user viewing the content.
"""

from moin.macros.Date import MacroDateTimeBase
from moin.utils import show_time


class Macro(MacroDateTimeBase):
    def macro(self, content, arguments, page_url, alternative):
        if arguments is None:
            tm = None
        else:
            stamp = arguments[0]
            tm = self.parse_time(stamp)
        return show_time.format_date_time(tm)
