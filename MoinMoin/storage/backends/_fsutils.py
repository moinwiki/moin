# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - helper for fs based backends
"""


import re

from MoinMoin import config


# Precompiled patterns for file name [un]quoting
UNSAFE = re.compile(r'[^a-zA-Z0-9_]+')
QUOTED = re.compile(r'\(([a-fA-F0-9]+)\)')


def quoteWikinameFS(wikiname, charset=config.charset):
    """ Return file system representation of a Unicode WikiName.

    Warning: will raise UnicodeError if wikiname can not be encoded using
    charset. The default value of config.charset, 'utf-8' can encode any
    character.

    @param wikiname: wiki name [unicode]
    @param charset: charset to encode string (before quoting)
    @rtype: string
    @return: quoted name, safe for any file system
    """
    filename = wikiname.encode(charset)

    quoted = []
    location = 0
    for needle in UNSAFE.finditer(filename):
        # append leading safe stuff
        quoted.append(filename[location:needle.start()])
        location = needle.end()
        # Quote and append unsafe stuff
        quoted.append('(')
        for character in needle.group():
            quoted.append('%02x' % ord(character))
        quoted.append(')')

    # append rest of string
    quoted.append(filename[location:])
    return ''.join(quoted)


class InvalidFileNameError(Exception):
    """ Called when we find an invalid file name """
    pass


def unquoteWikiname(filename, charset=config.charset):
    """ Return Unicode WikiName from quoted file name.

    raises an InvalidFileNameError in case of unquoting problems.

    @param filename: quoted wiki name
    @param charset: charset to use for decoding (after unquoting)
    @rtype: unicode
    @return: WikiName
    """
    # From some places we get called with Unicode strings
    if isinstance(filename, unicode):
        filename = filename.encode(config.charset)

    parts = []
    start = 0
    for needle in QUOTED.finditer(filename):
        # append leading unquoted stuff
        parts.append(filename[start:needle.start()])
        start = needle.end()
        # Append quoted stuff
        group = needle.group(1)
        # Filter invalid filenames
        if (len(group) % 2 != 0):
            raise InvalidFileNameError(filename)
        try:
            for i in range(0, len(group), 2):
                byte = group[i:i+2]
                character = chr(int(byte, 16))
                parts.append(character)
        except ValueError:
            # byte not in hex, e.g 'xy'
            raise InvalidFileNameError(filename)

    # append rest of string
    if start == 0:
        wikiname = filename
    else:
        parts.append(filename[start:len(filename)])
        wikiname = ''.join(parts)

    return wikiname.decode(charset)

