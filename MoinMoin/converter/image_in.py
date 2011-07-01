# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Image converter

Convert image to <object> tag for the DOM Tree.
"""


from emeraldtree import ElementTree as ET

from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Convert an image to the corresponding <object> in the DOM Tree
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls(input_type=input)

    def __init__(self, input_type):
        self.input_type = input_type

    def __call__(self, rev):
        item_name = rev.item.name
        attrib = {
            moin_page.type_: unicode(self.input_type),
            xlink.href: Iri(scheme='wiki', authority='', path='/'+item_name, query='do=get&rev=%d' % rev.revno),
        }
        return moin_page.object_(attrib=attrib, children=[item_name, ])


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('image/svg+xml'), type_moin_document)
default_registry.register(Converter._factory, Type('image/png'), type_moin_document)
default_registry.register(Converter._factory, Type('image/jpeg'), type_moin_document)
default_registry.register(Converter._factory, Type('image/gif'), type_moin_document)

