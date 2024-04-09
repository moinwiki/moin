# Copyright: 2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Arguments support for wiki formats
"""

import re

from ._args import Arguments

# default parsing rules, splits on blank spaces, see parse() docstring for example
# input: can be like: a b c d=e f="g h" i='j k' l="\"m\" n" o='\'p\' q'
_parse_rules = r"""
(?:
    ([-&\w]+)
    =
)?
(?:
    ([-\w]+)
    |
    "
    (.*?)
    (?<!\\)"
    |
    '
    (.*?)
    (?<!\\)'
)
"""
parse_re = re.compile(_parse_rules, re.X | re.U)

# parsing rules for object keyword parameters, similar to default parsing rules, but
# input value may have trailing %: width=100%
_parse_rules = r"""
(?:
    ([-&\w]+)
    =
)?
(?:
    ([-\w]+%*)  # added `%*` to default rules
    |
    "
    (.*?)
    (?<!\\)"
    |
    '
    (.*?)
    (?<!\\)'
)
"""
object_re = re.compile(_parse_rules, re.X | re.U)

# rules for include macro, splits on commas, allows leading ^ and embedded /
# <<Include(pagename, heading, level, from="regex", to="regex", sort=ascending|descending,
#           items=n, skipitems=n, titlesonly, editlink)>>
# <<Include(^Prefix..-..-..,,to="^----",sort=descending,items=3)>>
_include_rules = r"""
(?:
    ([-&\w]+)
    =
)?
(?:
    (\^?[-/\.\w\d]+[-\s\w]*)  # pagenames like "jpeg.jpg", "/sub/my page"
    |
    "
    (.*?)
    (?<!\\)"
    |
    '
    (.*?)
    (?<!\\)'
)
"""
include_re = re.compile(_include_rules, re.X | re.U)


def parse(input, parse_re=parse_re):
    """
    Parse <input> for positional and keyword arguments, with value quoting and quotes escaping.

    :param input: with default parse_re, can be like: a b c d=e f="g h" i='j k' l="\"m\" n" o='\'p\' q'
    :param parse_re: a compiled re pattern or None
    :returns: Argument instance
    """
    ret = Arguments()
    for match in parse_re.finditer(input):
        key = match.group(1)
        value = (
            (match.group(2) or match.group(3) or match.group(4))
            .encode("ascii", errors="backslashreplace")
            .decode("unicode-escape")
        )
        if key:
            ret.keyword[key] = value
        else:
            ret.positional.append(value)
    return ret


_unparse_rules = r"""^[-\w]+$"""
_unparse_re = re.compile(_unparse_rules, re.X)


def unparse(args):
    """
    Generate a argument string from a Argument instance <args>.
    Argument values that need quoting will be quoted.
    Keyword names must never need quoting (would raise ValueError).

    :param args: Argument instance
    :returns: argument unicode object
    """

    def quote(s):
        return '"%s"' % s.encode("unicode-escape").decode("ascii")

    ret = []

    for value in args.positional:
        if not _unparse_re.match(value):
            value = quote(value)
        ret.append(value)

    keywords = list(args.keyword.items())
    keywords.sort(key=lambda a: a[0])
    for key, value in keywords:
        if not _unparse_re.match(key):
            raise ValueError("Invalid keyword string")
        if not _unparse_re.match(value):
            value = quote(value)
        ret.append(key + "=" + value)

    return " ".join(ret)
