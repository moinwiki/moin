#!/usr/bin/python
# Copyright: 2013 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Alternative to the Unix dos2unix utility that can run on either Windows or Unix. Does not implement
the typical Unix dos2unix command-line syntax.

If the passed parameter is a directory, all files in that directory are converted to Unix line endings.
Subdirectories are not processed. If the passed parameter is a filename, only that filename is converted.

Usage: python path/to/dos2unix.py <target_directory_or_filename>
"""

import os
import sys


def convert_file(filename):
    """Replace DOS line endings with Unix line endings."""
    with open(filename, "rb") as f:
        data = f.read()
    if "\0" in data:
        # is binary file
        return
    newdata = data.replace("\r\n", "\n")
    if newdata != data:
        with open(filename, "wb") as f:
            f.write(newdata)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        target = sys.argv[1]
        if os.path.isdir(target):
            for dirpath, dirnames, filenames in os.walk(target):
                break
            for filename in filenames:
                convert_file(os.path.join(target, filename))
        elif os.path.isfile(target):
            convert_file(target)
        else:
            print("Error: %s does not exist." % target)
    else:
        print("Error: incorrect parameters passed.")
        print("usage: python <path_to>dos2unix.py <target_directory>")
