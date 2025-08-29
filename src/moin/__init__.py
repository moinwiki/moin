# Copyright: 2000-2006 by Juergen Hermann <jh@web.de>
# Copyright: 2002-2018 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin — a wiki engine written in Python.
"""


import sys
import platform

from ._version import version  # noqa

project = "MoinMoin"


if sys.hexversion < 0x3090000:
    sys.exit("Error: %s requires Python 3.9 or later; current version is %s\n" % (project, platform.python_version()))
