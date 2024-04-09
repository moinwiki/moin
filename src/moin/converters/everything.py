# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - converter for all items (fallback)

Convert any item to a DOM Tree (we just create a link to download it).
"""


from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document
from moin.i18n import _

from . import default_registry


class Converter:
    """
    Convert a unsupported item to DOM Tree.
    """

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        try:
            item_name = rev.item.name or rev.meta["name"][0]
        except IndexError:
            # item is deleted
            message = _(
                "This deleted item must be restored before it can be viewed or downloaded, ItemID = {itemid}"
            ).format(itemid=rev.item.itemid)
            admonition = moin_page.div(attrib={moin_page.class_: "error"}, children=[moin_page.p(children=[message])])
            body = moin_page.body(children=(admonition,))
            return moin_page.page(children=(body,))
        attrib = {xlink.href: Iri(scheme="wiki", authority="", path="/" + item_name, query=f"do=get&rev={rev.revid}")}
        a = moin_page.a(attrib=attrib, children=[f"Download {item_name}."])
        body = moin_page.body(children=(a,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type("application/octet-stream"), type_moin_document)
default_registry.register(Converter._factory, Type(type=None, subtype=None), type_moin_document)
