#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Print statistics gathered by hotshot profiler

    Usage:
        print_stats.py statsfile

    Typical usage:
     1. Edit moin.py and activate the hotshot profiler, set profile file name
     2. Run moin.py
     3. Do some request, with a browser, script or ab
     4. Stop moin.py
     5. Run this tool: print_stats.py moin.prof

    Currently CGI and twisted also have a hotshot profiler integration.

    @copyright: 2005 by Thomas Waldmann (MoinMoin:ThomasWaldmann)
    @license: GNU GPL, see COPYING for details.
"""
def run():
    import sys
    from hotshot import stats

    if len(sys.argv) != 2:
        print __doc__
        sys.exit()

    # Load and print stats
    s = stats.load(sys.argv[1])
    s.strip_dirs()
    s.sort_stats('cumulative', 'time', 'calls')
    s.print_stats(40)
    s.print_callers(40)

if __name__ == "__main__":
    run()

