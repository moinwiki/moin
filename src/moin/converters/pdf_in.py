# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - PDF input converter
"""

import io
from datetime import datetime, timedelta

from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from pdfminer3.layout import LAParams

from . import default_registry
from moin.utils.mime import Type, type_text_plain

from moin import log
logging = log.getLogger(__name__)


LAPARAMS = LAParams()


class PDFIndexingConverter:
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, rev, contenttype=None, arguments=None):
        rsrcmgr = PDFResourceManager()
        max_parse_time = timedelta(seconds=15)
        start = datetime.now()
        with io.StringIO() as f, TextConverter(rsrcmgr, f, laparams=LAPARAMS) as device:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page_idx, page in enumerate(PDFPage.get_pages(rev)):
                logging.debug("Processing PDF page %d", page_idx)
                interpreter.process_page(page)
                if datetime.now() - start > max_parse_time:
                    logging.info("PDF parsing timed out after %d pages", page_idx)
                    break
            logging.debug("PDF text extraction took: %s", datetime.now() - start)
            return f.getvalue()


default_registry.register(PDFIndexingConverter._factory, Type('application/pdf'), type_text_plain)
