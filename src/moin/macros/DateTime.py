# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin DateTime macro - outputs the date and time for some specific point in time,
adapted to the TZ settings of the user viewing the content.
"""

from moin.macros._base import fail_message
from moin.macros.Date import MacroDateTimeBase
from moin.utils import show_time
from moin.i18n import _


class Macro(MacroDateTimeBase):
    """
    Return a date and time formatted per user settings or an error message if input is invalid.
    """

    def macro(self, content, arguments, page_url, alternative):
        if arguments is None:
            tm = None
        else:
            tm = arguments[0]
        try:
            if tm:
                tm = self.parse_time(tm)
            return show_time.format_date_time(tm)
        except (AttributeError, OSError, AssertionError, ValueError, OverflowError):
            err_msg = _("Invalid input parameter: None, float, int, or ISO 8601 formats are accepted.")
            return fail_message(err_msg, alternative)
