# Copyright: 2006 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - simple text diff (uses difflib).
"""


import difflib


def diff(oldlines, newlines, **kw):
    """
    Find changes between oldlines and newlines.

    :param oldlines: List of old text lines.
    :param newlines: List of new text lines.
    :keyword ignorews: If 1, ignore whitespace.
    :rtype: list
    :returns: Lines like the diff tool outputs.
    """
    false = lambda s: None  # noqa
    if kw.get("ignorews", 0):
        d = difflib.Differ(false)
    else:
        d = difflib.Differ(false, false)

    lines = list(d.compare(oldlines, newlines))

    # Return an empty list if there were no changes
    changed = 0
    for line in lines:
        if line[0] != " ":
            changed = 1
            break
    if not changed:
        return []

    #    if not "we want the unchanged lines, too":
    #        if "no questionmark lines":
    #            lines = [line for line in lines if line[0] != '?']
    #        return lines

    # Calculate the hunks and remove the unchanged lines between them
    i = 0  # actual index in lines
    count = 0  # number of unchanged lines
    lcount_old = 0  # line count old file
    lcount_new = 0  # line count new file
    while i < len(lines):
        marker = lines[i][0]
        if marker == " ":
            count += 1
            i += 1
            lcount_old += 1
            lcount_new += 1
        elif marker in ["-", "+"]:
            if (count == i) and count > 3:
                lines[: i - 3] = []
                i = 4
                count = 0
            elif count > 6:
                # remove lines and insert new hunk indicator
                lines[i - count + 3 : i - 3] = [f"@@ -{lcount_old:d}, +{lcount_new:d} @@\n"]
                i = i - count + 8
                count = 0
            else:
                count = 0
                i += 1
            if marker == "-":
                lcount_old += 1
            else:
                lcount_new += 1
        elif marker == "?":
            lines[i : i + 1] = []

    # Remove unchanged lines at the end
    if count > 3:
        lines[-count + 3 :] = []

    return lines
