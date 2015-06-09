# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - PDF input converter
"""


from __future__ import absolute_import, division

from pdfminer.pdfparser import PDFDocument, PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, process_pdf
from pdfminer.pdfdevice import PDFDevice
from pdfminer.converter import TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams

from MoinMoin import log
logging = log.getLogger(__name__)


LAPARAMS = LAParams(
    # value is specified not as an actual length, but as a proportion of the length to the
    # size of each character in question.
    # two text chunks whose distance is closer than the char_margin is considered
    # continuous and get grouped into one.
    char_margin=0.3,
    # it may be required to insert blank characters (spaces) as necessary if the distance
    # between two words is greater than the word_margin, as a blank between words might
    # not be represented as a space, but indicated by the positioning of each word.
    word_margin=0.2,
    # two lines whose distance is closer than the line_margin is grouped as a text box,
    # which is a rectangular area that contains a "cluster" of text portions.
    line_margin=0.3,
)


class UnicodeConverter(TextConverter):
    # as result, we want a unicode object
    # TextConverter only provides encoded output into a file-like object
    def __init__(self, rsrcmgr, pageno=1, laparams=None, showpageno=False):
        TextConverter.__init__(self, rsrcmgr, None, codec=None, pageno=pageno, laparams=laparams,
                               showpageno=showpageno)
        self.__text = []

    def write_text(self, text):
        self.__text.append(text)

    def read_result(self):
        return u''.join(self.__text)


class PDFIndexingConverter(object):
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        rsrcmgr = PDFResourceManager()
        device = UnicodeConverter(rsrcmgr, laparams=LAPARAMS)
        try:
            process_pdf(rsrcmgr, device, rev)
            return device.read_result()
        finally:
            device.close()


from . import default_registry
from MoinMoin.util.mime import Type, type_text_plain
default_registry.register(PDFIndexingConverter._factory, Type('application/pdf'), type_text_plain)
