# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - OpenDocument Format (ODF) input converter

ODF documents can be created with OpenOffice.org, Libre Office and other software.
"""

import zipfile

from moin.constants.keys import NAME
from moin.utils.mime import Type, type_text_plain

from . import default_registry
from .xml_in import strip_xml

from moin import log

logging = log.getLogger(__name__)


class OpenDocumentIndexingConverter:
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        zf = zipfile.ZipFile(rev, "r")  # rev is file-like
        try:
            data = zf.read("content.xml")
            text = data.decode("utf-8")
            text = strip_xml(text)
            return text
        except AttributeError as e:
            logging.warning(f"Content of file {rev.meta[NAME]} is not seekable. {str(e)}")
        finally:
            zf.close()


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


# use same converter for the old *.sx? (pre-opendocument) openoffice documents:
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
