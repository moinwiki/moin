# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter for all items (fallback)

Convert any item to a DOM Tree (we just create a link to download it).
"""


from emeraldtree import ElementTree as ET

from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document

from . import default_registry


class Converter:
    """
    Convert a unsupported item to DOM Tree.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        item_name = rev.item.name or rev.meta['name'][0]
        attrib = {
            xlink.href: Iri(scheme='wiki', authority='', path='/' + item_name,
                            query='do=get&rev={0}'.format(rev.revid)),
        }
        a = moin_page.a(attrib=attrib, children=["Download {0}.".format(item_name)])
        body = moin_page.body(children=(a, ))
        return moin_page.page(children=(body, ))


default_registry.register(Converter._factory, Type('application/octet-stream'), type_moin_document)
default_registry.register(Converter._factory, Type(type=None, subtype=None), type_moin_document)
