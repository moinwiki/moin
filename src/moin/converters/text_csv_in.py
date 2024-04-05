# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - CSV text data to DOM converter
"""

import csv

from ._table import TableMixin
from ._util import decode_data, normalize_split_text
from moin.utils.tree import moin_page
from moin.i18n import _

from . import default_registry
from moin.utils.mime import Type, type_moin_document


class Converter(TableMixin):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def _factory(cls, type_input, type_output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        # prevent incorrect output when there are multiple trailing blank lines
        text = text.rstrip()
        content = normalize_split_text(text)
        dialect = csv.Sniffer().sniff(text)
        reader = csv.reader(content, dialect)
        rows = list(reader)
        head = None
        cls = None
        try:
            # fragile function, throws errors when csv file is incorrectly formatted
            if csv.Sniffer().has_header("\n".join(content)):
                head = rows[0]
                rows = rows[1:]
                cls = "moin-sortable"
        except csv.Error as e:
            head = [_("Error parsing CSV file:"), str(e)]
        table = self.build_dom_table(rows, head=head, cls=cls)
        body = moin_page.body(children=(table,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type("text/csv"), type_moin_document)
