# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2018 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - a wiki engine in Python.
"""


import sys
import platform

from ._version import version

project = "MoinMoin"


if sys.hexversion < 0x3080000:
    sys.exit("Error: %s requires Python 3.8+, current version is %s\n" % (project, platform.python_version()))
