# Copyright: 2001-2003 Juergen Hermann <jh@web.de>
# Copyright: 2003-2006 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Clock
"""


import time
from functools import wraps, partial

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import g as flaskg


class Clock(object):
    """
    Helper class for measuring the time needed to run code.

    Usage:
        flaskg.clock.start('mytimer')
        # do something
        flaskg.clock.stop('mytimer')
        # or if you want to use its value later
        timerval = flaskg.clock.stop('mytimer')

    Starting a timer multiple times is supported but the
    one started last has to be stopped first.
    """

    def __init__(self):
        self.timers = {}

    def start(self, timer):
        if timer not in self.timers:
            self.timers[timer] = []
        self.timers[timer].append(time.time())

    def stop(self, timer):
        if timer in self.timers:
            value = time.time() - self.timers[timer].pop()
            logging.info('timer {0}({1}): {2:.2f}ms'.format(timer, len(self.timers[timer]), value * 1000))
            if not self.timers[timer]:
                del self.timers[timer]
            return value

    def __del__(self):
        if self.timers:
            logging.warning('These timers have not been stopped: {0}'.format(', '.join(self.timers.keys())))


def add_timing(f, name=None):
    if name is None:
        name = f.__name__

    @wraps(f)
    def wrapper(*args, **kw):
        flaskg.clock.start(name)
        retval = f(*args, **kw)
        flaskg.clock.stop(name)
        return retval
    return wrapper


def timed(name=None):
    return partial(add_timing, name=name)
