"""
    MoinMoin - signalling support

    MoinMoin uses blinker for sending signals and letting listeners subscribe
    to signals.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

# import all signals so they can be imported from here:
from signals import *

# import all signal handler modules so they install their handlers:
import log

