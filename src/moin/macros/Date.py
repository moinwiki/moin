# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin Date macro - outputs the date for some specific point in time,
adapted to the TZ settings of the user viewing the content.
"""


import time

from moin.macros._base import MacroInlineBase, fail_message
from moin.utils import show_time
from moin.i18n import _


class MacroDateTimeBase(MacroInlineBase):
    def parse_time(self, args):
        """
        Parse a time specification argument for usage by Date and DateTime macro.
        Not all ISO 8601 format variations are accepted as input.

        :param args: float/int UNIX timestamp or None or ISO 8601 formatted date time:
                     YYYY-MM-DDTHH:MM:SS (plus optional Z or z for UTC, or +/-HHMM) or
                     YYYY-MM-DD HH:MM:SS (same as above but replacing T separator with " ")
        :returns: UNIX timestamp (UTC) or raises one of AttributeError, OSError, AssertionError, ValueError, OverflowError
        """
        if (
            len(args) >= 19
            and args[4] == "-"
            and args[7] == "-"
            and args[10] in "T "
            and args[13] == ":"
            and args[16] == ":"
        ):
            year, month, day = int(args[0:4]), int(args[5:7]), int(args[8:10])
            hour, minute, second = int(args[11:13]), int(args[14:16]), int(args[17:19])
            tz = args[19:]  # +HHMM, -HHMM or Z or nothing (then we assume Z)
            tzoffset = 0  # we assume UTC no matter if there is a Z
            if tz:
                sign = tz[0]
                if sign in "+-\u2212":  # ascii plus, ascii hyphen-minus, unicode minus
                    tzh, tzm = int(tz[1:3]), int(tz[3:])
                    tzoffset = (tzh * 60 + tzm) * 60
                    if sign in "-\u2212":  # ascii hyphen-minus, unicode minus
                        tzoffset = -tzoffset
            tm = year, month, day, hour, minute, second, 0, 0, 0

            # as mktime wants a localtime argument (but we only have UTC),
            # we adjust by our local timezone's offset
            tm = time.mktime(tm) - time.timezone - tzoffset
        else:
            tm = float(args)
        return tm


class Macro(MacroDateTimeBase):
    """
    Return a date formatted per user settings or an error message if input is invalid.
    """

    def macro(self, content, arguments, page_url, alternative):

        if arguments is None:
            tm = None  # show today's date
        else:
            tm = arguments[0]
        try:
            if tm:
                tm = self.parse_time(tm)
            return show_time.format_date(tm)
        except (AttributeError, OSError, AssertionError, ValueError, OverflowError):
            err_msg = _("Invalid input parameter: None, float, int, or ISO 8601 formats are accepted.")
            return fail_message(err_msg, alternative)
