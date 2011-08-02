# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - OpenDocument Format (ODF) input converter

ODF documents can be created with OpenOffice.org, Libre Office and other software.
"""


import re, zipfile

from MoinMoin import log
logging = log.getLogger(__name__)

rx_stripxml = re.compile("<[^>]*?>", re.DOTALL|re.MULTILINE)


class OpenDocumentIndexingConverter(object):
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        zf = zipfile.ZipFile(rev, "r")  # rev is file-like
        try:
            data = zf.read("content.xml")
            data = ' '.join(rx_stripxml.sub(" ", data).split())
            return data.decode('utf-8')
        finally:
            zf.close()


from . import default_registry
from MoinMoin.util.mime import Type, type_text_plain

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

