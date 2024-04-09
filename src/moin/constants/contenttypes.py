# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - contenttype related constants
"""

from collections import defaultdict
from moin.i18n import _


# Charset - we support only 'utf-8'. While older encodings might work,
# we don't have the resources to test them, and there is no real
# benefit for the user. IMPORTANT: use only lowercase 'utf-8'!
CHARSET = "utf-8"
CHARSET19 = "utf-8"

# Parser to use mimetype text
PARSER_TEXT_MIMETYPE = [
    "plain",
    "csv",
    "rst",
    "docbook",
    "latex",
    "tex",
    "html",
    "css",
    "xml",
    "python",
    "perl",
    "php",
    "ruby",
    "javascript",
    "cplusplus",
    "java",
    "pascal",
    "diff",
    "gettext",
    "xslt",
    "creole",
]

CONTENTTYPE_USER = "application/x.moin.userprofile"
CONTENTTYPE_DEFAULT = "application/octet-stream"
CONTENTTYPE_NONEXISTENT = "application/x-nonexistent"

CONTENTTYPE_MARKUP = [
    "text/x.moin.wiki;charset=utf-8",
    "text/x-mediawiki;charset=utf-8",
    "text/x.moin.creole;charset=utf-8",
    "text/x-markdown;charset=utf-8",
    "text/x-rst;charset=utf-8",
    "text/html;charset=utf-8",
    "application/docbook+xml;charset=utf-8",
]

CONTENTTYPE_MARKUP_OUT = {
    "moinwiki": "text/x.moin.wiki;charset=utf-8",
    # 'mediawiki': 'text/x-mediawiki;charset=utf-8',  # no output converter
    # 'creole': 'text/x.moin.creole;charset=utf-8',  # no output converter
    "markdown": "text/x-markdown;charset=utf-8",
    "rst": "text/x-rst;charset=utf-8",
    "html": "text/html;charset=utf-8",
    "docbook": "application/docbook+xml;charset=utf-8",
}

CONTENTTYPE_NO_EXPANSION = [
    # no need to expand transclusions, etc. when converting to/from these types
    "text/x.moin.wiki;charset=utf-8",
    "text/x.moin.creole;charset=utf-8",
]

CONTENTTYPE_VARIABLES = [
    # content types that support variables: @SIG@, @EMAIL@, @TIME@, @DATE@, etc
    "text/x.moin.wiki;charset=utf-8",
    "text/x.moin.wiki;format=1.9;charset=utf-8",
]

CONTENTTYPE_MOIN_19 = ["text/x.moin.wiki;format=1.9;charset=utf-8"]

CONTENTTYPE_TEXT = [
    "text/plain;charset=utf-8",
    "text/x-diff;charset=utf-8",
    "text/x-python;charset=utf-8",
    "text/csv;charset=utf-8",
    "text/x-irclog;charset=utf-8",
]

CONTENTTYPE_IMAGE = ["image/svg+xml", "image/png", "image/jpeg", "image/gif"]

CONTENTTYPE_AUDIO = ["audio/wave", "audio/ogg", "audio/mpeg", "audio/webm"]

CONTENTTYPE_VIDEO = ["video/ogg", "video/webm", "video/mp4"]

# TODO: is there a source that maps all (or common) file suffixes to media contenttypes as used by /maint/dump_html.py
CONTENTTYPE_MEDIA = CONTENTTYPE_VIDEO + CONTENTTYPE_AUDIO + CONTENTTYPE_IMAGE
CONTENTTYPE_MEDIA_SUFFIX = tuple(
    ".svg .png .jpg .jpeg .gif .wave .wav .ogg .oga .ogv.mpeg .mpg .mp3 .webm .mp4".split()
)

CONTENTTYPE_DRAWING = ["application/x-svgdraw"]

CONTENTTYPE_OTHER = [
    "application/octet-stream",
    "application/x-tar",
    "application/x-gtar",
    "application/zip",
    "application/pdf",
]

CONTENTTYPES_MAP = {
    "text/x.moin.wiki;charset=utf-8": "Moinmoin",
    "text/x.moin.wiki;format=1.9;charset=utf-8": "Moinmoin 1.9",
    "text/x-mediawiki;charset=utf-8": "MediaWiki",
    "text/x.moin.creole;charset=utf-8": "Creole",
    "text/x-markdown;charset=utf-8": "Markdown",
    "text/x-rst;charset=utf-8": "ReST",
    "text/html;charset=utf-8": "HTML",
    "application/docbook+xml;charset=utf-8": "DocBook",
    "text/plain;charset=utf-8": "Plain Text",
    "text/x-diff;charset=utf-8": "Diff/Patch",
    "text/x-python;charset=utf-8": "Python Code",
    "text/csv;charset=utf-8": "CSV",
    "text/x-irclog;charset=utf-8": "IRC Log",
    "image/svg+xml": "SVG Image",
    "image/png": "PNG Image",
    "image/jpeg": "JPEG Image",
    "image/gif": "GIF Image",
    "audio/wave": "WAV Audio",
    "audio/ogg": "OGG Audio",
    "audio/mpeg": "MP3 Audio",
    "audio/webm": "WebM Audio",
    "video/ogg": "OGG Video",
    "video/webm": "WebM Video",
    "video/mp4": "MP4 Video",
    "application/x-svgdraw": "SVGDRAW",
    "application/octet-stream": "Binary File",
    "application/x-tar": "TAR",
    "application/x-gtar": "TGZ",
    "application/zip": "ZIP",
    "application/pdf": "PDF",
}

GROUP_MARKUP_TEXT = "Markup Text Items"
GROUP_OTHER_TEXT = "Other Text Items"
GROUP_IMAGE = "Image Items"
GROUP_AUDIO = "Audio Items"
GROUP_VIDEO = "Video Items"
GROUP_DRAWING = "Drawing Items"
GROUP_OTHER = "Other Items"

DRAWING_EXTENSIONS = [".svg", ".png", ".jpg", ".jpeg", ".gif"]


# help for wiki editors based on content type
def ext_link(href, link_text=None):
    return '<a class="moin-http" href="%s">%s</a>' % (href, link_text or href)


help_on_plain_text = _("This is a plain text item, there is no markup.")
help_on_binary = _("This item can not be edited, upload a revised file.")
help_on_csv = " ".join(
    (
        _("Use a semicolon or comma to separate cells."),
        _("If the first row is recognized as a header, the table will be sortable."),
        ext_link("https://en.wikipedia.org/wiki/Comma-separated_values"),
    )
)


CONTENTTYPES_HELP_DOCS = {
    # content type: tuple - content type, button text; link generated later based on user preferred language
    "text/x.moin.wiki;charset=utf-8": (("moin", _("Click for help on Moin Wiki markup."))),
    "text/x.moin.wiki;format=1.9;charset=utf-8": (("moin", _("Moinmoin 1.9 format is deprecated, convert to moin 2."))),
    "text/x-mediawiki;charset=utf-8": (("mediawiki", _("Click for help on Media Wiki markup."))),
    "text/x.moin.creole;charset=utf-8": (("creole", _("Click for help on Creole Wiki markup."))),
    "text/x-markdown;charset=utf-8": (("markdown", _("Click for help on Markdown Wiki markup."))),
    "text/x-rst;charset=utf-8": (("rst", _("Click for help on reST Wiki markup."))),
    "application/docbook+xml;charset=utf-8": (("docbook", _("Click for help on Docbook Wiki markup."))),
    # content type: help string
    "text/html;charset=utf-8": ext_link("http://ckeditor.com/"),
    "text/plain;charset=utf-8": help_on_plain_text,
    "text/x-diff;charset=utf-8": help_on_plain_text,
    "text/x-python;charset=utf-8": help_on_plain_text,
    "text/csv;charset=utf-8": help_on_csv,
    "text/x-irclog;charset=utf-8": help_on_plain_text,
    "image/svg+xml": help_on_binary,
    "image/png": help_on_binary,
    "image/jpeg": help_on_binary,
    "image/gif": help_on_binary,
    "audio/wave": help_on_binary,
    "audio/ogg": help_on_binary,
    "audio/mpeg": help_on_binary,
    "audio/webm": help_on_binary,
    "video/ogg": help_on_binary,
    "video/webm": help_on_binary,
    "video/mp4": help_on_binary,
    "application/x-svgdraw": ext_link("http://code.google.com/p/svg-edit/"),
    "application/octet-stream": help_on_binary,
    "application/x-tar": help_on_binary,
    "application/x-gtar": help_on_binary,
    "application/zip": help_on_binary,
    "application/pdf": help_on_binary,
}
CONTENTTYPES_HELP_DOCS = defaultdict(lambda: _("No help for unknown content type."), CONTENTTYPES_HELP_DOCS)
