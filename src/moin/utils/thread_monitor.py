# Copyright: 2006 Alexander Schremmer <alex AT alexanderweb DOT de>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    Thread monitor - Check the state of all threads.

    Just call activate_hook() as early as possible in program execution.
    Then you can trigger the output of tracebacks of all threads
    by calling trigger_dump().
"""


__all__ = "activate_hook trigger_dump dump_regularly".split()


import sys
import threading
import traceback
from time import sleep
from io import StringIO


class Monitor:
    def __init__(self):
        self.enabled = False
        assert hasattr(sys, "_current_frames")  # make sure we have py >= 2.5

    def activate_hook(self):
        """Activates the thread monitor hook. Note that this might interfere
        with any kind of profiler and some debugging extensions."""
        self.enabled = True

    def trigger_dump(self, dumpfile=None):
        """Triggers the dump of the tracebacks of all threads.
        If dumpfile is specified, it is used as the output file."""
        if not self.enabled:
            return
        dumpfile = dumpfile or sys.stderr
        cur_frames = sys._current_frames()
        for i in cur_frames:
            f = StringIO()
            print(f"\nDumping thread (id {i}):", file=f)
            traceback.print_stack(cur_frames[i], file=f)
            dumpfile.write(f.getvalue())

    def hook_enabled(self):
        """Returns true if the thread_monitor hook is enabled."""
        return self.enabled


def dump_regularly(seconds):
    """Dumps the tracebacks every 'seconds' seconds."""
    activate_hook()

    def background_dumper(seconds):
        while True:
            sleep(seconds)
            trigger_dump()

    threading.Thread(target=background_dumper, args=(seconds,)).start()


mon = Monitor()

activate_hook = mon.activate_hook
trigger_dump = mon.trigger_dump
hook_enabled = mon.hook_enabled
