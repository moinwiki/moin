# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - misc. constants not fitting elsewhere
"""

import re

ANON = u'anonymous'

# Invalid characters - invisible characters that should not be in page
# names. Prevent user confusion and wiki abuse, e.g u'\u202aFrontPage'.
ITEM_INVALID_CHARS_REGEX = re.compile(
    ur"""
    \u0000 | # NULL

    # Bidi control characters
    \u202A | # LRE
    \u202B | # RLE
    \u202C | # PDF
    \u202D | # LRM
    \u202E   # RLM
    """,
    re.UNICODE | re.VERBOSE
)

CLEAN_INPUT_TRANSLATION_MAP = {
    # these chars will be replaced by blanks
    ord(u'\t'): u' ',
    ord(u'\r'): u' ',
    ord(u'\n'): u' ',
}
for c in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f':
    # these chars will be removed
    CLEAN_INPUT_TRANSLATION_MAP[ord(c)] = None
del c

# Other stuff
URI_SCHEMES = [
    'http', 'https', 'ftp', 'file',
    'mailto', 'nntp', 'news',
    'ssh', 'telnet', 'irc', 'ircs', 'xmpp', 'mumble',
    'webcal', 'ed2k', 'apt', 'rootz',
    'gopher',
    'notes',
    'rtp', 'rtsp', 'rtcp',
]
