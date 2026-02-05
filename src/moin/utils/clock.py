# Copyright: 2001-2003 Juergen Hermann <jh@web.de>
# Copyright: 2003-2006 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - clock utilities.
"""

from __future__ import annotations

import time

from typing import ParamSpec, TypeVar
from collections.abc import Callable
from functools import wraps, partial

from flask import g as flaskg

from moin import log

logging = log.getLogger(__name__)


class Clock:
    """
    Helper class for measuring the time needed to run code.

    Usage:
        flaskg.clock.start("mytimer")
        # Do something
        flaskg.clock.stop("mytimer", comment="Adds this to the log message")
        # The optional comment is appended to the log message.
        # Or, if you want to use its value later:
        timerval = flaskg.clock.stop("mytimer")

    Starting a timer multiple times is supported, but the
    one started last must be stopped first.
    """

    def __init__(self):
        self.timers = {}

    def start(self, timer):
        if timer not in self.timers:
            self.timers[timer] = []
        self.timers[timer].append(time.time())

    def stop(self, timer, comment=""):
        if timer in self.timers:
            value = time.time() - self.timers[timer].pop(0)
            logging.debug(f"timer {timer}({len(self.timers[timer])}): {value * 1000:.2f}ms {comment}")
            if not self.timers[timer]:
                del self.timers[timer]
            return value

    def __del__(self):
        if self.timers:
            logging.warning(f"These timers have not been stopped: {', '.join(self.timers.keys())}")


P = ParamSpec("P")
R = TypeVar("R")


def add_timing(f: Callable[P, R], name: str | None = None) -> Callable[P, R]:
    if name is None:
        name = f.__name__

    @wraps(f)
    def wrapper(*args: P.args, **kw: P.kwargs) -> R:
        flaskg.clock.start(name)
        retval = f(*args, **kw)
        flaskg.clock.stop(name)
        return retval

    return wrapper


def timed(name: str | None = None):
    return partial(add_timing, name=name)
