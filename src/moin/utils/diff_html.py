# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2002 Scott Moonen <smoonen@andstuff.org>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Side by side diffs
"""


import difflib

from markupsafe import escape


def indent(line):
    eol = ""
    while line and line[0] == "\n":
        eol += "\n"
        line = line[1:]
    stripped = line.lstrip()
    if len(line) - len(stripped):
        line = "&nbsp;" * (len(line) - len(stripped)) + stripped
    # return "%d / %d / %s" % (len(line), len(stripped), line)
    return eol + line


# This code originally by Scott Moonen, used with permission.
def diff(old, new):
    """Find changes between old and new and return
    HTML markup visualising them.

    :param old: old text [unicode]
    :param new: new text [unicode]
    """
    seq1 = old.splitlines()
    seq2 = new.splitlines()

    seqobj = difflib.SequenceMatcher(None, seq1, seq2)
    linematch = seqobj.get_matching_blocks()

    result = []

    if len(seq1) == len(seq2) and linematch[0] == (0, 0, len(seq1)):
        return result

    lastmatch = (0, 0)

    # Print all differences
    for match in linematch:
        # Starts of pages identical?
        if lastmatch == match[0:2]:
            lastmatch = (match[0] + match[2], match[1] + match[2])
            continue
        llineno, rlineno = lastmatch[0] + 1, lastmatch[1] + 1
        leftpane = ""
        rightpane = ""
        linecount = max(match[0] - lastmatch[0], match[1] - lastmatch[1])
        for line in range(linecount):
            if line < match[0] - lastmatch[0]:
                if line > 0:
                    leftpane += "\n"
                leftpane += seq1[lastmatch[0] + line]
            if line < match[1] - lastmatch[1]:
                if line > 0:
                    rightpane += "\n"
                rightpane += seq2[lastmatch[1] + line]

        charobj = difflib.SequenceMatcher(None, leftpane, rightpane)
        charmatch = charobj.get_matching_blocks()

        if charobj.ratio() < 0.5:
            # Insufficient similarity.
            if leftpane:
                leftresult = f"""<span>{indent(str(escape(leftpane)))}</span>"""
            else:
                leftresult = ""

            if rightpane:
                rightresult = f"""<span>{indent(str(escape(rightpane)))}</span>"""
            else:
                rightresult = ""
        else:
            # Some similarities; markup changes.
            charlast = (0, 0)
            leftresult = ""
            rightresult = ""
            for thismatch in charmatch:
                if thismatch[0] - charlast[0] != 0:
                    leftresult += """<span>{}</span>""".format(indent(escape(leftpane[charlast[0] : thismatch[0]])))
                if thismatch[1] - charlast[1] != 0:
                    rightresult += """<span>{}</span>""".format(indent(escape(rightpane[charlast[1] : thismatch[1]])))
                leftresult += str(escape(leftpane[thismatch[0] : thismatch[0] + thismatch[2]]))
                rightresult += str(escape(rightpane[thismatch[1] : thismatch[1] + thismatch[2]]))
                charlast = (thismatch[0] + thismatch[2], thismatch[1] + thismatch[2])

        leftpane = "<br>".join([indent(x) for x in leftresult.splitlines()])
        rightpane = "<br>".join([indent(x) for x in rightresult.splitlines()])
        result.append((llineno, leftpane, rlineno, rightpane))

        lastmatch = (match[0] + match[2], match[1] + match[2])

    return result
