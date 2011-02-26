"""
MoinMoin - a wiki engine in Python.

@copyright: 2000-2006 by Juergen Hermann <jh@web.de>,
            2002-2011 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import os
import sys

project = "MoinMoin"

if sys.hexversion < 0x2060000:
    sys.exit("%s requires Python 2.6 or greater.\n" % project)


from MoinMoin.util.version import Version

version = Version(2, 0, 0, 'a0')

