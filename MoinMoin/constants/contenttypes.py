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


GROUP_MARKUP_TEXT = 'markup text items'
GROUP_OTHER_TEXT = 'other text items'
GROUP_IMAGE = 'image items'
GROUP_AUDIO = 'audio items'
GROUP_VIDEO = 'video items'
GROUP_DRAWING = 'drawing items'
GROUP_OTHER = 'other items'
