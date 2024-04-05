# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter for non-existing items

Convert a non-existent item to the DOM Tree.
"""


from moin.constants.contenttypes import CONTENTTYPE_NONEXISTENT
from moin.i18n import _
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document

from . import default_registry


class Converter:
    """
    Convert a non-existing item to DOM Tree.
    """

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        item_name = rev.item.fqname.fullname
        attrib = {xlink.href: Iri(scheme="wiki", authority="", path="/" + item_name, query="do=modify")}
        a = moin_page.a(
            attrib=attrib, children=[_("{item_name} does not exist. Create it? ").format(item_name=item_name)]
        )
        body = moin_page.body(children=(a,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type(CONTENTTYPE_NONEXISTENT), type_moin_document)
