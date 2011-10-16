# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - helpers for 1.9 migration
"""

import re

from MoinMoin.config import NAME, ACL, CONTENTTYPE, MTIME, LANGUAGE

CHARSET = 'utf-8'

# Precompiled patterns for file name [un]quoting
UNSAFE = re.compile(r'[^a-zA-Z0-9_]+')
QUOTED = re.compile(r'\(([a-fA-F0-9]+)\)')


def split_body(body):
    """
    Extract the processing instructions / acl / etc. at the beginning of a page's body.

    Hint: if you have a Page object p, you already have the result of this function in
          p.meta and (even better) parsed/processed stuff in p.pi.

    Returns a list of (pi, restofline) tuples and a string with the rest of the body.
    """
    pi = {}
    while body.startswith('#'):
        try:
            line, body = body.split('\n', 1) # extract first line
            line = line.rstrip('\r')
        except ValueError:
            line = body
            body = ''

        # end parsing on empty (invalid) PI
        if line == "#":
            body = line + '\n' + body
            break

        if line[1] == '#':# two hash marks are a comment
            comment = line[2:]
            if not comment.startswith(' '):
                # we don't require a blank after the ##, so we put one there
                comment = ' ' + comment
                line = '##{0}'.format(comment)

        verb, args = (line[1:] + ' ').split(' ', 1) # split at the first blank
        pi.setdefault(verb.lower(), []).append(args.strip())

    for key, value in pi.iteritems():
        if key in ['#', ]:
            # transform the lists to tuples:
            pi[key] = tuple(value)
        elif key in ['acl', ]:
            # join the list of values to a single value
            pi[key] = u' '.join(value)
        else:
            # for keys that can't occur multiple times, don't use a list:
            pi[key] = value[-1] # use the last value to copy 1.9 parsing behaviour

    return pi, body


def add_metadata_to_body(metadata, data):
    """
    Adds the processing instructions to the data.
    """
    meta_keys = [NAME, ACL, CONTENTTYPE, MTIME, LANGUAGE, ]

    metadata_data = ""
    for key, value in metadata.iteritems():
        if key not in meta_keys:
            continue
        # special handling for list metadata
        if isinstance(value, (list, tuple)):
            for line in value:
                metadata_data += "#{0} {1}\n".format(key, line)
        else:
            metadata_data += "#{0} {1}\n".format(key, value)
    return metadata_data + data


def quoteWikinameFS(wikiname, charset=CHARSET):
    """
    Return file system representation of a Unicode WikiName.

    Warning: will raise UnicodeError if wikiname can not be encoded using
    charset. The default value 'utf-8' can encode any character.

    :param wikiname: wiki name [unicode]
    :param charset: charset to encode string (before quoting)
    :rtype: string
    :returns: quoted name, safe for any file system
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
            quoted.append("{0:02x}".format(ord(character)))
        quoted.append(')')

    # append rest of string
    quoted.append(filename[location:])
    return ''.join(quoted)


class InvalidFileNameError(Exception):
    """ Called when we find an invalid file name """
    pass


def unquoteWikiname(filename, charset=CHARSET):
    """
    Return Unicode WikiName from quoted file name.

    raises an InvalidFileNameError in case of unquoting problems.

    :param filename: quoted wiki name
    :param charset: charset to use for decoding (after unquoting)
    :rtype: unicode
    :returns: WikiName
    """
    # From some places we get called with Unicode strings
    if isinstance(filename, unicode):
        filename = filename.encode(CHARSET)

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

