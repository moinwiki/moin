# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Generic XML input converter
"""

from __future__ import absolute_import, division

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from ._util import decode_data

RX_STRIPXML = re.compile(u"<[^>]*?>", re.U|re.DOTALL|re.MULTILINE)

def strip_xml(text):
    text = RX_STRIPXML.sub(u" ", text)
    text = ' '.join(text.split())
    return text


class XMLIndexingConverter(object):
    """
    We try to generically extract contents from XML documents by just throwing
    away all XML tags. This is for indexing, so this might be good enough.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        text = decode_data(rev, contenttype)
        text = strip_xml(text)
        return text


from . import default_registry
from MoinMoin.util.mime import Type, type_text_plain
default_registry.register(XMLIndexingConverter._factory, Type('text/xml'), type_text_plain)

