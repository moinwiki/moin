# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter for all items (fallback)

Convert any item to a DOM Tree (we just create a link to download it).
"""


from emeraldtree import ElementTree as ET

from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Convert a unsupported item to DOM Tree.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content):
        item_name = content # we just give the name of the item in the content
        attrib = {
            xlink.href: Iri(scheme='wiki', authority='', path='/'+item_name, query='do=get'),
        }
        return moin_page.a(attrib=attrib, children=["Download %s." % item_name])


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('application/octet-stream'), type_moin_document,
                          default_registry.PRIORITY_MIDDLE + 3)
default_registry.register(Converter._factory, Type(type=None, subtype=None), type_moin_document,
                          default_registry.PRIORITY_MIDDLE + 3)

