#!/usr/bin/env python
# Copyright: 2012 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Detect and correct violations of the moin2 coding standards:
    - no trailing blanks
    - exactly one linefeed at file end, see PEP8
    - DOS line endings on .bat and .cmd files, unix line endings everywhere else

Execute this script from the root directory of the moin2 repository or
from anywhere within the contrib path.
"""

import sys
import os


# file types to be processed
SELECTED_SUFFIXES = set("py bat cmd html css js styl".split())

# stuff considered DOS/WIN
WIN_SUFFIXES = set("bat cmd".split())


class NoDupsLogger(object):
    """Suppress duplicate messages."""
    def __init__(self):
        self.seen = set()

    def log(self, msg):
        if msg not in self.seen:
            print msg
            self.seen.add(msg)


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
        force a single linefeed at file end,
        force line ending to be \r\n for bat files and \n for all others."""
    suffix = suffix.lower()
    if suffix in WIN_SUFFIXES:
        line_end = "\r\n"
    else:
        line_end = "\n"
    logger = NoDupsLogger()

    with open(filename, "rb") as f:
        lines = f.readlines()

    # now look at file end and get rid of all whitespace-only lines there:
    while lines:
        if not lines[-1].strip():
            del lines[-1]
            logger.log(u"%s was changed to remove empty lines at eof" % filename)
        else:
            break

    with open(filename, "wb") as f:
        for line in lines:
            length_line = len(line)
            line = line.replace('\t', '    ')
            if len(line) != length_line:
                logger.log(u"%s was changed to replace tab characters with 4 spaces" % filename)
            pep8_line = line.rstrip() + line_end
            f.write(pep8_line)
            # if line was changed, issue warning once for each type of change
            if suffix in WIN_SUFFIXES and not line.endswith("\r\n"):
                logger.log(u"%s was changed to DOS line endings" % filename)
            elif suffix not in WIN_SUFFIXES and line.endswith("\r\n"):
                logger.log(u"%s was changed to Unix line endings" % filename)
            elif pep8_line != line:
                if len(pep8_line) < len(line):
                    logger.log(u"%s was changed to remove trailing blanks" % filename)
                else:
                    logger.log(u"%s was changed to add end of line character at end of file" % filename)


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
            if suffix in SELECTED_SUFFIXES:
                filename = os.path.join(root, file)
                check_files(filename, suffix)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        starting_dir = os.path.abspath(sys.argv[1])
    else:
        starting_dir = os.path.abspath(os.path.dirname(__file__))
        starting_dir = starting_dir.split(os.sep + 'contrib')[0]
    NoDupsLogger().log(u"Starting directory is %s" % starting_dir)
    file_picker(starting_dir)
