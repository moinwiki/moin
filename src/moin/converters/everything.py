# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Converter for all items (fallback).

Convert any item to a DOM tree (we just create a link to download it).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from moin.constants.keys import NAME
from moin.i18n import _
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document

from . import default_registry

if TYPE_CHECKING:
    from emeraldtree.ElementTree import Element
    from moin.converters._args import Arguments
    from typing_extensions import Self


def make_message_page(text: str, class_: str = "error") -> Element:
    admonition = moin_page.div(attrib={moin_page.class_: class_}, children=[moin_page.p(children=[text])])
    body = moin_page.body(children=(admonition,))
    return moin_page.page(children=(body,))


class Converter:
    """
    Convert an unsupported item to a DOM tree.
    """

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs) -> Self:
        return cls()

    def __call__(self, rev: Any, contenttype: str | None = None, arguments: Arguments | None = None) -> Element:

        try:
            item_name = rev.item.fqname.fullname or rev.meta[NAME][0]
        except IndexError:
            # item is deleted
            message = _(
                "This deleted item must be restored before it can be viewed or downloaded, ItemID = {itemid}"
            ).format(itemid=rev.item.itemid)
            return make_message_page(message)
        except AttributeError:
            # conversion only works for instances of Revision or DummyRev
            message = _("No DOM representation possible for this content.")
            return make_message_page(message, "note")

        attrib = {xlink.href: Iri(scheme="wiki", authority="", path="/" + item_name, query=f"do=get&rev={rev.revid}")}
        a = moin_page.a(attrib=attrib, children=[_("Download {item_name}.").format(item_name=item_name)])
        body = moin_page.body(children=(a,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type("application/octet-stream"), type_moin_document)
default_registry.register(Converter._factory, Type(type=None, subtype=None), type_moin_document)
