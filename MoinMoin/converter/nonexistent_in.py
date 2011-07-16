# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter for non-existing items

Convert a non-existent item to the DOM Tree.
"""


from emeraldtree import ElementTree as ET

from MoinMoin.i18n import _, L_, N_
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Convert a non-existing item to DOM Tree.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        item_name = rev.item.name
        attrib = {
            xlink.href: Iri(scheme='wiki', authority='', path='/'+item_name, query='do=modify'),
        }
        return moin_page.a(attrib=attrib, children=[_("%(item_name)s does not exist. Create it?", item_name=item_name)])


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('application/x-nonexistent'), type_moin_document)

