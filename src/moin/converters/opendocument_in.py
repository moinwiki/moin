# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - OpenDocument Format (ODF) input converter.

ODF documents can be created with OpenOffice.org, LibreOffice, and other software.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import zipfile
import zlib

from moin.constants.keys import NAME
from moin.converters.base import ConverterBase
from moin.log import getLogger
from moin.utils.mime import Type, type_text_plain

from . import default_registry
from .xml_in import strip_xml

if TYPE_CHECKING:
    from moin.converters._args import Arguments
    from moin.storage.middleware.indexing import Revision
    from typing_extensions import Self

logger = getLogger(__name__)


class OpenDocumentIndexingConverter(ConverterBase):

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs: Any) -> Self:
        return cls(**kwargs)

    def __call__(self, rev: Revision, contenttype: str | None = None, arguments: Arguments | None = None) -> str:
        try:
            with zipfile.ZipFile(rev.data, "r") as zf:  # rev.data is file-like
                data = zf.read("content.xml")
            text = data.decode("utf-8")
            text = strip_xml(text)
            return text
        except (
            KeyError,
            zipfile.BadZipFile,
            UnicodeDecodeError,
            OSError,
            AttributeError,
            zlib.error,
            RuntimeError,
            NotImplementedError,
        ) as e:
            logger.warning(f"Content of file {rev.meta[NAME]} could not be read: {e}")
            return ""


opendocument_types = """\
application/vnd.oasis.opendocument.chart
application/vnd.oasis.opendocument.database
application/vnd.oasis.opendocument.formula
application/vnd.oasis.opendocument.graphics
application/vnd.oasis.opendocument.graphics-template
application/vnd.oasis.opendocument.image
application/vnd.oasis.opendocument.presentation
application/vnd.oasis.opendocument.presentation-template
application/vnd.oasis.opendocument.spreadsheet
application/vnd.oasis.opendocument.spreadsheet-template
application/vnd.oasis.opendocument.text
application/vnd.oasis.opendocument.text-master
application/vnd.oasis.opendocument.text-template
application/vnd.oasis.opendocument.text-web""".split()

for t in opendocument_types:
    default_registry.register(OpenDocumentIndexingConverter._factory, Type(t), type_text_plain)


# Use the same converter for the old *.sx? (pre-OpenDocument) OpenOffice documents:
OpenOfficeIndexingConverter = OpenDocumentIndexingConverter

openoffice_types = """\
application/vnd.sun.xml.calc
application/vnd.sun.xml.draw
application/vnd.sun.xml.impress
application/vnd.sun.xml.math
application/vnd.sun.xml.writer
application/vnd.sun.xml.writer.global""".split()

for t in openoffice_types:
    default_registry.register(OpenOfficeIndexingConverter._factory, Type(t), type_text_plain)
