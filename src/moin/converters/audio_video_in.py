# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Audio/Video converter.

Convert an audio/video file to an <object> tag for the DOM tree.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from . import default_registry
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink, html
from moin.utils.mime import Type, type_moin_document
from moin.constants.keys import SUMMARY

if TYPE_CHECKING:
    from moin.converters._args import Arguments
    from moin.storage.middleware.indexing import Revision
    from typing_extensions import Self


class Converter:
    """
    Convert an audio/video file to the corresponding <object> in the DOM tree.
    """

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs: Any) -> Self:
        return cls(input_type=input)

    def __init__(self, input_type: Type) -> None:
        self.input_type = input_type

    def __call__(self, rev: Revision, contenttype: str | None = None, arguments: Arguments | None = None) -> Any:
        item_name = rev.item.fqname.fullname
        attrib = {
            moin_page.type_: str(self.input_type),
            xlink.href: Iri(scheme="wiki", authority="", path="/" + item_name, query=f"do=get&rev={rev.revid}"),
        }
        if arguments and html.alt in arguments:
            attrib[html.alt] = arguments[html.alt]
        elif rev.meta.get(SUMMARY):
            attrib[html.alt] = rev.meta[SUMMARY]
        obj = moin_page.object_(attrib=attrib, children=["Your Browser does not support HTML5 audio/video element."])
        body = moin_page.body(children=(obj,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type("video/mp4"), type_moin_document)
default_registry.register(Converter._factory, Type("video/ogg"), type_moin_document)
default_registry.register(Converter._factory, Type("video/webm"), type_moin_document)

default_registry.register(Converter._factory, Type("audio/mpeg"), type_moin_document)
default_registry.register(Converter._factory, Type("audio/ogg"), type_moin_document)
default_registry.register(Converter._factory, Type("audio/webm"), type_moin_document)
default_registry.register(Converter._factory, Type("audio/x-wav"), type_moin_document)
