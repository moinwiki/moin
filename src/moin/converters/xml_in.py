# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Generic XML input converter.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import re

from . import default_registry
from ._util import decode_data

from moin import log
from moin.utils.mime import Type, type_text_plain

if TYPE_CHECKING:
    from moin.converters._args import Arguments
    from moin.storage.middleware.indexing import Revision
    from typing_extensions import Self

logging = log.getLogger(__name__)


RX_STRIPXML = re.compile("<[^>]*?>", re.U | re.DOTALL | re.MULTILINE)


def strip_xml(text):
    text = RX_STRIPXML.sub(" ", text)
    text = " ".join(text.split())
    return text


class XMLIndexingConverter:
    """
    We try to generically extract contents from XML documents by just throwing
    away all XML tags. This is for indexing, so this might be good enough.
    """

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs: Any) -> Self:
        return cls()

    def __call__(self, rev: Revision, contenttype: str | None = None, arguments: Arguments | None = None) -> Any:
        text = decode_data(rev, contenttype)
        text = strip_xml(text)
        return text


default_registry.register(XMLIndexingConverter._factory, Type("text/xml"), type_text_plain)
