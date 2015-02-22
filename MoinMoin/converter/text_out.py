# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - plain text output converter

Converts an internal document tree into plain, unformatted text.

The purpose of this converter is mainly to be used in a converter chain like
markup -> dom -> text and get rid of the (wiki, rst, docbook, ...) markup that
way, so we get indexable plain text for our search index.
"""


from __future__ import absolute_import, division


class Converter(object):
    """
    Converter application/x.moin.document -> text/plain
    """
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, root):
        return u'\n'.join(root.itertext())


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document, type_text_plain
default_registry.register(Converter.factory, type_moin_document, type_text_plain)
