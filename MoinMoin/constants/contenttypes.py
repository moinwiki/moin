# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - contenttype related constants
"""

# Charset - we support only 'utf-8'. While older encodings might work,
# we don't have the resources to test them, and there is no real
# benefit for the user. IMPORTANT: use only lowercase 'utf-8'!
charset = 'utf-8'

# Parser to use mimetype text
parser_text_mimetype = ('plain', 'csv', 'rst', 'docbook', 'latex', 'tex', 'html', 'css',
                       'xml', 'python', 'perl', 'php', 'ruby', 'javascript',
                       'cplusplus', 'java', 'pascal', 'diff', 'gettext', 'xslt', 'creole', )

CONTENTTYPE_USER = u'application/x.moin.userprofile'
CONTENTTYPE_DEFAULT = u'application/octet-stream'

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

