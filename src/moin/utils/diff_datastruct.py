# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import difflib
from collections.abc import Hashable

INSERT = "insert"
DELETE = "delete"
REPLACE = "replace"


class UndefinedType:
    """Represents a non-existing value"""


Undefined = UndefinedType()


def diff(d1, d2, basekeys=None):
    """Get the diff of 2 datastructures (usually 2 meta dicts)

    :param d1: old datastructure
    :param d2: new datastructure
    :param basekeys: list of data keys' basenames (default: None, meaning [])
    :return: a list of tuples of the format (<change type>, <basekeys>, <value>)
             that can be used to format a diff
    """
    if basekeys is None:
        basekeys = []
    changes = []

    if isinstance(d1, UndefinedType) and isinstance(d2, (dict, list)):
        d1 = type(d2)()
    elif isinstance(d2, UndefinedType) and isinstance(d1, (dict, list)):
        d2 = type(d1)()
    if isinstance(d1, dict) and isinstance(d2, dict):
        added = set(d2) - set(d1)
        removed = set(d1) - set(d2)
        all_ = set(d1) | set(d2)
        for key in sorted(all_):
            keys = basekeys + [key]
            if key in added:
                changes.extend(diff(Undefined, d2[key], keys))
            elif key in removed:
                changes.extend(diff(d1[key], Undefined, keys))
            else:
                changes.extend(diff(d1[key], d2[key], keys))
    elif isinstance(d1, list) and isinstance(d2, list):
        hashable = all(isinstance(d1, str) or all(isinstance(v, Hashable) for v in d) for d in [d1, d2])
        if hashable:
            matches = difflib.SequenceMatcher(None, d1, d2)
            for tag, d1_start, d1_end, d2_start, d2_end in matches.get_opcodes():
                if tag == REPLACE:
                    changes.extend([(DELETE, basekeys, d1[d1_start:d1_end]), (INSERT, basekeys, d2[d2_start:d2_end])])
                elif tag == DELETE:
                    changes.append((DELETE, basekeys, d1[d1_start:d1_end]))
                elif tag == INSERT:
                    changes.append((INSERT, basekeys, d2[d2_start:d2_end]))
        else:
            changes.extend(diff(str(d1), str(d2), basekeys))
    elif any(isinstance(d, (type(None), bool, int, float, str)) for d in (d1, d2)):
        if isinstance(d1, UndefinedType):
            changes.append((INSERT, basekeys, d2))
        elif isinstance(d2, UndefinedType):
            changes.append((DELETE, basekeys, d1))
        elif isinstance(d1, type(d2)):
            if d1 != d2:
                changes.extend([(DELETE, basekeys, d1), (INSERT, basekeys, d2)])
        else:
            raise TypeError("Unsupported diff between {} and {} data types".format(type(d1), type(d2)))
    else:
        raise TypeError("Unsupported diff between {} and {} data types".format(type(d1), type(d2)))
    return changes


def make_text_diff(changes):
    """Transform change tuples into text diffs

    :param changes: a list of tuples of the format (<change type>, <basekeys>, <value>)
                    that represent a diff
    :return: a generator of text diffs
    """
    marker = {INSERT: "+", DELETE: "-"}
    for change_type, keys, value in changes:
        yield "{} {}{}{}".format(
            marker[change_type], ".".join(str(key) for key in keys), ": " if keys else "", str(value)
        )
