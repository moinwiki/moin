#!/usr/bin/python
# Copyright: 2013 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Alternative for unix dos2unix utility that may be run on either windows or unix. Does not implement
typical unix dos2unix command line syntax.

If passed parameter is a directory, all files in that directory are converted to unix line endings.
Sub-directories are not processed.  If passed parameter is a filename, only that filename is converted.

Usage: python <path_to>dos2unix.py <target_directory_or_filename>
"""

import os
import sys


def convert_file(filename):
    """Replace DOS line endings with unix line endings."""
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
