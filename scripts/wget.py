#!/usr/bin/python
# Copyright: 2013 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Alternative to the Unix wget utility that can run on either Windows or Unix. Does not implement
the typical Unix wget command-line syntax.

Usage: python path/to/wget.py <url> <output_file>
"""

import sys
import urllib.request


if __name__ == "__main__":
    if len(sys.argv) == 3:
        urllib.request.urlretrieve(sys.argv[1], sys.argv[2])
    else:
        print("Error: incorrect parameters passed.")
        print("Usage: python path/to/wget.py <url> <output_file>")
