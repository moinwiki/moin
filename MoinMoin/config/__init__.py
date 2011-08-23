# Copyright: 2005-2006,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - site-wide configuration defaults (NOT per single wiki!)
"""

import re

# unicode: set the char types (upper, lower, digits, spaces)
from MoinMoin.util.chartypes import *

# Parser to use mimetype text
parser_text_mimetype = ('plain', 'csv', 'rst', 'docbook', 'latex', 'tex', 'html', 'css',
                       'xml', 'python', 'perl', 'php', 'ruby', 'javascript',
                       'cplusplus', 'java', 'pascal', 'diff', 'gettext', 'xslt', 'creole', )

# Charset - we support only 'utf-8'. While older encodings might work,
# we don't have the resources to test them, and there is no real
# benefit for the user. IMPORTANT: use only lowercase 'utf-8'!
charset = 'utf-8'

# Invalid characters - invisible characters that should not be in page
# names. Prevent user confusion and wiki abuse, e.g u'\u202aFrontPage'.
page_invalid_chars_regex = re.compile(
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

# used for wikiutil.clean_input
clean_input_translation_map = {
    # these chars will be replaced by blanks
    ord(u'\t'): u' ',
    ord(u'\r'): u' ',
    ord(u'\n'): u' ',
}
for c in u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f' \
          '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f':
    # these chars will be removed
    clean_input_translation_map[ord(c)] = None
del c

# Other stuff
url_schemas = ['http', 'https', 'ftp', 'file',
               'mailto', 'nntp', 'news',
               'ssh', 'telnet', 'irc', 'ircs', 'xmpp', 'mumble',
               'webcal', 'ed2k', 'apt', 'rootz',
               'gopher',
               'notes',
               'rtp', 'rtsp', 'rtcp',
              ]


# ACL rights that are valid in moin2
SUPERUSER = 'superuser'
NOTEXTCHA = 'notextcha'
# rights that control access to specific functionality
ACL_RIGHTS_FUNCTIONS = [SUPERUSER, NOTEXTCHA, ]

ADMIN = 'admin'
READ = 'read'
WRITE = 'write'
CREATE = 'create'
DESTROY = 'destroy'
# rights that control access to operations on contents
ACL_RIGHTS_CONTENTS = [READ, WRITE, CREATE, ADMIN, DESTROY, ]

# metadata keys
UUID = "uuid"
NAME = "name"
NAME_OLD = "name_old"

# if an item is reverted, we store the revision number we used for reverting there:
REVERTED_TO = "reverted_to"

# some metadata key constants:
ACL = "acl"

# This says: I am a system item
IS_SYSITEM = "is_syspage"
# This says: original sysitem as contained in release: <release>
SYSITEM_VERSION = "syspage_version"

# keys for storing group and dict information
# group of user names, e.g. for ACLs:
USERGROUP = "usergroup"
# needs more precise name / use case:
SOMEDICT = "somedict"

CONTENTTYPE = "contenttype"
SIZE = "size"
LANGUAGE = "language"
ITEMLINKS = "itemlinks"
ITEMTRANSCLUSIONS = "itemtransclusions"
TAGS = "tags"

ACTION = "action"
ADDRESS = "address"
HOSTNAME = "hostname"
USERID = "userid"
MTIME = "mtime"
EXTRA = "extra"
COMMENT = "comment"

# we need a specific hash algorithm to store hashes of revision data into meta
# data. meta[HASH_ALGORITHM] = hash(rev_data, HASH_ALGORITHM)
# some backends may use this also for other purposes.
HASH_ALGORITHM = 'sha1'

# structure for contenttype groups
CONTENTTYPE_GROUPS = [
    ('markup text items', [
        ('text/x.moin.wiki;charset=utf-8', 'Wiki (MoinMoin)'),
        ('text/x.moin.creole;charset=utf-8', 'Wiki (Creole)'),
        ('text/x-mediawiki;charset=utf-8', 'Wiki (MediaWiki)'),
        ('text/x-rst;charset=utf-8', 'ReST'),
        ('application/docbook+xml;charset=utf-8', 'DocBook'),
        ('text/html;charset=utf-8', 'HTML'),
    ]),
    ('other text items', [
        ('text/plain;charset=utf-8', 'plain text'),
        ('text/x-diff;charset=utf-8', 'diff/patch'),
        ('text/x-python;charset=utf-8', 'python code'),
        ('text/csv;charset=utf-8', 'csv'),
        ('text/x-irclog;charset=utf-8', 'IRC log'),
    ]),
    ('image items', [
        ('image/jpeg', 'JPEG'),
        ('image/png', 'PNG'),
        ('image/svg+xml', 'SVG'),
    ]),
    ('audio items', [
        ('audio/wave', 'WAV'),
        ('audio/ogg', 'OGG'),
        ('audio/mpeg', 'MP3'),
        ('audio/webm', 'WebM'),
    ]),
    ('video items', [
        ('video/ogg', 'OGG'),
        ('video/webm', 'WebM'),
        ('video/mp4', 'MP4'),
    ]),
    ('drawing items', [
        ('application/x-twikidraw', 'TDRAW'),
        ('application/x-anywikidraw', 'ADRAW'),
        ('application/x-svgdraw', 'SVGDRAW'),
    ]),
    ('other items', [
        ('application/pdf', 'PDF'),
        ('application/zip', 'ZIP'),
        ('application/x-tar', 'TAR'),
        ('application/x-gtar', 'TGZ'),
        ('application/octet-stream', 'binary file'),
    ]),
]

