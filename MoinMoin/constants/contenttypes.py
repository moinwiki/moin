# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - contenttype related constants
"""

# Charset - we support only 'utf-8'. While older encodings might work,
# we don't have the resources to test them, and there is no real
# benefit for the user. IMPORTANT: use only lowercase 'utf-8'!
CHARSET = 'utf-8'

# Parser to use mimetype text
PARSER_TEXT_MIMETYPE = [
    'plain', 'csv', 'rst', 'docbook', 'latex', 'tex', 'html', 'css',
    'xml', 'python', 'perl', 'php', 'ruby', 'javascript',
    'cplusplus', 'java', 'pascal', 'diff', 'gettext', 'xslt', 'creole',
]

CONTENTTYPE_USER = u'application/x.moin.userprofile'
CONTENTTYPE_DEFAULT = u'application/octet-stream'
CONTENTTYPE_NONEXISTENT = u'application/x-nonexistent'

CONTENTTYPE_MARKUP = [
    u'text/x.moin.wiki;charset=utf-8',
    u'text/x-mediawiki;charset=utf-8',
    u'text/x.moin.creole;charset=utf-8',
    u'text/x-markdown;charset=utf-8',
    u'text/x-rst;charset=utf-8',
    u'text/html;charset=utf-8',
    u'application/docbook+xml;charset=utf-8',
]

CONTENTTYPE_TEXT = [
    u'text/plain;charset=utf-8',
    u'text/x-diff;charset=utf-8',
    u'text/x-python;charset=utf-8',
    u'text/csv;charset=utf-8',
    u'text/x-irclog;charset=utf-8',
]

CONTENTTYPE_IMAGE = [
    u'image/svg+xml',
    u'image/png',
    u'image/jpeg',
    u'image/gif',
]

CONTENTTYPE_AUDIO = [
    u'audio/wave',
    u'audio/ogg',
    u'audio/mpeg',
    u'audio/webm',
]

CONTENTTYPE_VIDEO = [
    u'video/ogg',
    u'video/webm',
    u'video/mp4',
]

CONTENTTYPE_DRAWING = [
    u'application/x-twikidraw',
    u'application/x-anywikidraw',
    u'application/x-svgdraw',
]

CONTENTTYPE_OTHER = [
    u'application/octet-stream',
    u'application/x-tar',
    u'application/x-gtar',
    u'application/zip',
    u'application/pdf',
]

CONTENTTYPES_MAP = {
    u'text/x.moin.wiki;charset=utf-8': 'Wiki (Moinmoin)',
    u'text/x-mediawiki;charset=utf-8': 'Wiki (MediaWiki)',
    u'text/x.moin.creole;charset=utf-8': 'Wiki (Creole)',
    u'text/x-markdown;charset=utf-8': 'Markdown',
    u'text/x-rst;charset=utf-8': 'ReST',
    u'text/html;charset=utf-8': 'HTML',
    u'application/docbook+xml;charset=utf-8': 'DocBook',
    u'text/plain;charset=utf-8': 'Plain Text',
    u'text/x-diff;charset=utf-8': 'Diff/Patch',
    u'text/x-python;charset=utf-8': 'Python Code',
    u'text/csv;charset=utf-8': 'CSV',
    u'text/x-irclog;charset=utf-8': 'IRC Log',
    u'image/svg+xml': 'SVG Image',
    u'image/png': 'PNG Image',
    u'image/jpeg': 'JPEG Image',
    u'image/gif': 'GIF Image',
    u'audio/wave': 'WAV Audio',
    u'audio/ogg': 'OGG Audio',
    u'audio/mpeg': 'MP3 Audio',
    u'audio/webm': 'WebM Audio',
    u'video/ogg': 'OGG Video',
    u'video/webm': 'WebM Video',
    u'video/mp4': 'MP4 Video',
    u'application/x-twikidraw': 'TDRAW',
    u'application/x-anywikidraw': 'ADRAW',
    u'application/x-svgdraw': 'SVGDRAW',
    u'application/octet-stream': 'Binary File',
    u'application/x-tar': 'TAR',
    u'application/x-gtar': 'TGZ',
    u'application/zip': 'ZIP',
    u'application/pdf': 'PDF',
}

GROUP_MARKUP_TEXT = 'Markup Text Items'
GROUP_OTHER_TEXT = 'Other Text Items'
GROUP_IMAGE = 'Image Items'
GROUP_AUDIO = 'Audio Items'
GROUP_VIDEO = 'Video Items'
GROUP_DRAWING = 'Drawing Items'
GROUP_OTHER = 'Other Items'

DRAWING_EXTENSIONS = ['.tdraw', '.adraw', '.svg', '.png', '.jpg', '.jpeg', '.gif', ]
