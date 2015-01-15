# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - contenttype related constants
"""

from collections import defaultdict
from MoinMoin.i18n import _, L_, N_


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


# help for wiki editors based on content type
def ext_link(href, link_text=None):
    return '<a class="moin-http" href="%s">%s</a>' % (href, link_text or href)


help_on_plain_text = _("This is a plain text item, there is no markup.")
help_on_binary = _("This item can not be edited, upload a revised file.")
help_on_csv = ' '.join((
    _("Use a semicolon or comma to separate cells."),
    _("If the first row is recognized as a header, the table will be sortable."),
    ext_link("https://en.wikipedia.org/wiki/Comma-separated_values"),
))

CONTENTTYPES_HELP_DOCS = {
    # content type: tuple - must defer forming url until wiki root is known
    u'text/x.moin.wiki;charset=utf-8': (('user/moinwiki.html', _("Click for help on Moin Wiki markup."))),
    u'text/x-mediawiki;charset=utf-8': (('user/mediawiki.html', _("Click for help on Media Wiki markup."))),
    u'text/x.moin.creole;charset=utf-8': (('user/creolewiki.html', _("Click for help on Creole Wiki markup."))),
    u'text/x-markdown;charset=utf-8': (('user/markdown.html', _("Click for help on Markdown Wiki markup."))),
    u'text/x-rst;charset=utf-8': (('user/rest.html', _("Click for help on ReST Wiki markup."))),
    u'application/docbook+xml;charset=utf-8': (('user/docbook.html', _("Click for help on Docbook Wiki markup."))),
    # content type: help string
    u'text/html;charset=utf-8': ext_link('http://ckeditor.com/'),
    u'text/plain;charset=utf-8': help_on_plain_text,
    u'text/x-diff;charset=utf-8': help_on_plain_text,
    u'text/x-python;charset=utf-8': help_on_plain_text,
    u'text/csv;charset=utf-8': help_on_csv,
    u'text/x-irclog;charset=utf-8': help_on_plain_text,
    u'image/svg+xml': help_on_binary,
    u'image/png': help_on_binary,
    u'image/jpeg': help_on_binary,
    u'image/gif': help_on_binary,
    u'audio/wave': help_on_binary,
    u'audio/ogg': help_on_binary,
    u'audio/mpeg': help_on_binary,
    u'audio/webm': help_on_binary,
    u'video/ogg': help_on_binary,
    u'video/webm': help_on_binary,
    u'video/mp4': help_on_binary,
    u'application/x-twikidraw': ext_link('http://twiki.org/cgi-bin/view/Plugins/TWikiDrawPlugin'),
    u'application/x-anywikidraw': ext_link('http://anywikidraw.sourceforge.net/'),
    u'application/x-svgdraw': ext_link('http://code.google.com/p/svg-edit/'),
    u'application/octet-stream': help_on_binary,
    u'application/x-tar': help_on_binary,
    u'application/x-gtar': help_on_binary,
    u'application/zip': help_on_binary,
    u'application/pdf': help_on_binary,
}
CONTENTTYPES_HELP_DOCS = defaultdict(lambda: _('No help for unknown content type.'), CONTENTTYPES_HELP_DOCS)
