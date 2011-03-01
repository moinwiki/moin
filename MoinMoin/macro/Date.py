# Copyright: 2008-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin Date macro - outputs the date for some specific point in time,
    adapted to the TZ settings of the user viewing the content.
"""


import time

from flask import flaskg
from flaskext.babel import format_date

from MoinMoin.macro._base import MacroInlineBase

class MacroDateTimeBase(MacroInlineBase):
    def parse_time(self, args):
        """ parse a time specification argument for usage by Date and DateTime macro

        :param args: YYYY-MM-DDTHH:MM:SS (plus optional Z for UTC, or +/-HHMM) or
                     float/int UNIX timestamp
        :returns: UNIX timestamp (UTC)
        """
        if args is None:
            tm = time.time() # always UTC
        elif (len(args) >= 19 and args[4] == '-' and args[7] == '-' and
              args[10] == 'T' and args[13] == ':' and args[16] == ':'):
            # we ignore any time zone offsets here, assume UTC,
            # and accept (and ignore) any trailing stuff
            try:
                year, month, day = int(args[0:4]), int(args[5:7]), int(args[8:10])
                hour, minute, second = int(args[11:13]), int(args[14:16]), int(args[17:19])
                tz = args[19:] # +HHMM, -HHMM or Z or nothing (then we assume Z)
                tzoffset = 0 # we assume UTC no matter if there is a Z
                if tz:
                    sign = tz[0]
                    if sign in '+-':
                        tzh, tzm = int(tz[1:3]), int(tz[3:])
                        tzoffset = (tzh * 60 + tzm) * 60
                        if sign == '-':
                            tzoffset = -tzoffset
                tm = year, month, day, hour, minute, second, 0, 0, 0
            except ValueError, err:
                raise ValueError("Bad timestamp %r: %s" % (args, err))
            # as mktime wants a localtime argument (but we only have UTC),
            # we adjust by our local timezone's offset
            try:
                tm = time.mktime(tm) - time.timezone - tzoffset
            except (OverflowError, ValueError):
                tm = 0 # incorrect, but we avoid an ugly backtrace
        else:
            # try raw seconds since epoch in UTC
            try:
                tm = float(args)
            except ValueError, err:
                raise ValueError("Bad timestamp %r: %s" % (args, err))
        return tm

class Macro(MacroDateTimeBase):
    def macro(self, stamp=None):
        tm = self.parse_time(stamp)
        return format_date(tm)

