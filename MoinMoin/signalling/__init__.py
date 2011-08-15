# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - signalling support

    MoinMoin uses blinker for sending signals and letting listeners subscribe
    to signals.
"""


# import all signals so they can be imported from here:
from .signals import *

# import all signal handler modules so they install their handlers:
from . import log

