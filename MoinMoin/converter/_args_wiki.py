# Copyright: 2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Arguments support for wiki formats
"""


from __future__ import absolute_import, division

import re

from ._args import Arguments

# see parse() docstring for example
_parse_rules = r'''
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
'''
_parse_re = re.compile(_parse_rules, re.X)


def parse(input):
    """
    Parse <input> for positional and keyword arguments, with value quoting and
    quotes escaping.

    :param input: can be like: a b c d=e f="g h" i='j k' l="\"m\" n" o='\'p\' q'
    :returns: Argument instance
    """
    ret = Arguments()

    for match in _parse_re.finditer(input):
        key = match.group(1)
        value = (match.group(2) or match.group(3) or match.group(4)).decode('unicode-escape')

        if key:
            ret.keyword[key] = value
        else:
            ret.positional.append(value)

    return ret


_unparse_rules = r'''^[-\w]+$'''
_unparse_re = re.compile(_unparse_rules, re.X)


def unparse(args):
    """
    Generate a argument string from a Argument instance <args>.
    Argument values that need quoting will be quoted.
    Keyword names must never need quoting (would raise ValueError).

    :param args: Argument instance
    :returns: argument unicode object
    """
    ret = []

    for value in args.positional:
        if not _unparse_re.match(value):
            value = u'"' + value.encode('unicode-escape') + u'"'
        ret.append(value)

    keywords = args.keyword.items()
    keywords.sort(key=lambda a: a[0])
    for key, value in keywords:
        if not _unparse_re.match(key):
            raise ValueError("Invalid keyword string")
        if not _unparse_re.match(value):
            value = u'"' + value.encode('unicode-escape') + u'"'
        ret.append(key + u'=' + value)

    return u' '.join(ret)
