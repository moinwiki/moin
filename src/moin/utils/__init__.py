# Copyright: 2004 Juergen Hermann, Thomas Waldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - utility functions.
General helper functions that are not directly wiki-related.
"""

from __future__ import annotations

import pickle
import re
from datetime import datetime, timezone
from importlib import import_module
from io import BytesIO
from moin.error import ConfigurationError
from xstatic.main import XStatic


# Set pickle protocol; see http://docs.python.org/lib/node64.html
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
    Convert a string to a CDATA-encoded one.
    Copyright (c) 1999-2000 FourThought
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_cdataCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: "&#x%02X;" % ord(m.group()), new_string)
    return new_string


def TranslateText(text):
    """
    Convert a string to a PCDATA-encoded one (do minimal encoding).
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
    Close a file so a Windows-based server can delete a recently viewed item's file.

    If not closed, attempts to delete an open file (before garbage collection removes it)
    will result in an error:
        The process cannot access the file because it is being used by another process.
    """
    # Some tests reuse BytesIO objects and will fail with I/O operation on closed file.
    if hasattr(f, "close") and not f.closed and not isinstance(f, BytesIO):
        f.close()


def utcfromtimestamp(timestamp):
    """Return a naive datetime representing the timestamp in the UTC time zone."""
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)


def utcnow():
    """Return a naive datetime representing the current time in the UTC time zone."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_xstatic_module_path_map(
    module_names: list[str], root_url: str = "/static", provider: str = "local", protocol: str = "http"
) -> dict[str, str]:
    path_map: dict[str, str] = {}
    for name in module_names:
        module_name = f"xstatic.pkg.{name}"
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as exc:
            raise ConfigurationError(
                f'The Python module "{module_name}" could not be found - check your configuration'
            ) from exc
        xs = XStatic(module, root_url, provider, protocol)
        path_map[xs.name] = xs.base_dir  # type: ignore
    return path_map
