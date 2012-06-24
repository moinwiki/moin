#!/usr/bin/env python
# Copyright: 2012 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Detect and correct violations of the moin2 coding standards:
    - no trailing blanks
    - blank line at file end
    - DOS line endings on .bat files, unix line endings everywhere else

Execute this script from the root directory of the moin2 repository or
from anywhere within the contrib path.
"""

import sys, os
import warnings
warnings.simplefilter("once")

# file types to be processed
selected_suffixes = "py bat html css js".split()

# directories to ignore
def directories_to_ignore(starting_dir):
    """Return a list of directories that will not be processed."""
    # list format: [(fully qualified directory name, sub-directory name), ... ]
    ignore_dirs = []
    level2_dirs = ".hg contrib dlc docs env moin.egg-info wiki".split()
    for dir in level2_dirs:
        ignore_dirs.append((starting_dir, dir))
    ignore_dirs.append((starting_dir + os.sep + "MoinMoin", "translations"))
    return ignore_dirs


def check_files(filename, suffix):
    """Delete trailing blanks,
        force blank line at file end,
        force line ending to be \r\n for bat files and \n for all others."""
    if suffix.lower() == "bat":
        line_end = "\r\n"
    else:
        line_end = "\n"

    with open(filename, "rb") as f:
        lines = f.readlines()

    with open(filename, "wb") as f:
        for line in lines:
            pep8_line = line.rstrip() + line_end
            f.write(pep8_line)
            # if line was changed, issue warning once for each type of change
            if suffix == "bat" and not line.endswith("\r\n"):
                warnings.warn("%s was changed to DOS line endings" % filename)
            elif suffix != "bat" and line.endswith("\r\n"):
                warnings.warn("%s was changed to Unix line endings" % filename)
            elif pep8_line != line:
                warnings.warn("%s was changed to remove trailing blanks" % filename)

        # add blank line at end of file if needed
        if lines and pep8_line != line_end:
            f.write(line_end)
            warnings.warn("%s was changed to add blank line to end of file" % filename)

def file_picker(starting_dir):
    """Select target files and pass each to file checker."""
    ignore_dirs = directories_to_ignore(starting_dir)

    for root, dirs, files in os.walk(starting_dir):
        # delete directories in ignore list
        for mama_dir, baby_dir in ignore_dirs:
            if mama_dir == root and baby_dir in dirs:
                dirs.remove(baby_dir)
        # check files with selected suffixes
        for file in files:
            suffix = file.split(".")[-1]
            if suffix in selected_suffixes:
                filename = os.path.join(root, file)
                check_files(filename, suffix)

if __name__ == "__main__":
    starting_dir = os.path.abspath(os.path.dirname(__file__))
    starting_dir = starting_dir.split(os.sep + 'contrib')[0]
    warnings.warn("%s is starting directory" % starting_dir)
    file_picker(starting_dir)

