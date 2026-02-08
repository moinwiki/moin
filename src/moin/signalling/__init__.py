# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - signalling support.

MoinMoin uses Blinker to send signals and let listeners subscribe to them.
"""

# import all signals so they can be imported from here:
from .signals import *  # noqa

# import all signal handler modules so they install their handlers:
from . import log  # noqa
