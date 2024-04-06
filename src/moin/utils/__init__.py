# Copyright: 2004 Juergen Hermann, Thomas Waldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Utility Functions
    General helper functions that are not directly wiki related.
"""


from datetime import datetime, timezone
import re
import pickle
from io import BytesIO

# Set pickle protocol, see http://docs.python.org/lib/node64.html
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


#############################################################################
# XML helper functions
#############################################################################

g_xmlIllegalCharPattern = re.compile("[\x01-\x08\x0B-\x0D\x0E-\x1F\x80-\xFF]")
g_undoUtf8Pattern = re.compile("\xC2([^\xC2])")
g_cdataCharPattern = re.compile("[&<'\"]")
g_textCharPattern = re.compile("[&<]")
g_charToEntity = {"&": "&amp;", "<": "&lt;", "'": "&apos;", '"': "&quot;"}


def TranslateCDATA(text):
    """
    Convert a string to a CDATA-encoded one
    Copyright (c) 1999-2000 FourThought
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_cdataCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: "&#x%02X;" % ord(m.group()), new_string)
    return new_string


def TranslateText(text):
    """
    Convert a string to a PCDATA-encoded one (do minimal encoding)
    Copyright (c) 1999-2000 FourThought
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_textCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: "&#x%02X;" % ord(m.group()), new_string)
    return new_string


#############################################################################
# Misc
#############################################################################


def rangelist(numbers):
    """Convert a list of integers to a range string in the form
    '1,2-5,7'.
    """
    numbers = sorted(numbers[:])
    numbers.append(999999)
    pattern = ","
    for i in range(len(numbers) - 1):
        if pattern[-1] == ",":
            pattern += str(numbers[i])
            if numbers[i] + 1 == numbers[i + 1]:
                pattern += "-"
            else:
                pattern += ","
        elif numbers[i] + 1 != numbers[i + 1]:
            pattern = pattern + str(numbers[i]) + ","

    if pattern[-1] in ",-":
        return pattern[1:-1]
    return pattern[1:]


def close_file(f):
    """
    Close a file so a Windows based server can destroy a recently viewed item's file.

    If not closed, attempts to destroy an open file (before garbage collection removes it)
    will result an error:
        The process cannot access the file because it is being used by another process.
    """
    # some tests reuse BytesIO objects and will fail with I/O operation on closed file.
    if hasattr(f, "close") and not f.closed and not isinstance(f, BytesIO):
        f.close()


def utcfromtimestamp(timestamp):
    """Returns a naive datetime instance representing the timestamp in the UTC timezone"""
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)


def utcnow():
    """Returns a naive datetime instance representing the current time in the UTC timezone"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
