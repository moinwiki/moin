# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - a wiki engine in Python.
"""


from __future__ import absolute_import, division

project = "MoinMoin"

import sys
if sys.hexversion < 0x2060000:
    sys.exit("%s requires Python 2.6 or greater.\n" % project)


from MoinMoin.util.version import Version

version = Version(2, 0, 0, 'a0')

