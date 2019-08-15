# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - PDF input converter
"""

import io

from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from pdfminer3.layout import LAParams

from . import default_registry
from moin.utils.mime import Type, type_text_plain

from moin import log
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


class PDFIndexingConverter:
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        rsrcmgr = PDFResourceManager()
        with io.StringIO() as f, TextConverter(rsrcmgr, f, laparams=LAPARAMS) as device:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.get_pages(rev):
                interpreter.process_page(page)
            return f.getvalue()


default_registry.register(PDFIndexingConverter._factory, Type('application/pdf'), type_text_plain)
