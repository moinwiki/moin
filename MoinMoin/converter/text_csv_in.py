# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - CSV text data to DOM converter
"""


from __future__ import absolute_import, division

import csv

from ._table import TableMixin
from ._util import decode_data, normalize_split_text


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
        content = normalize_split_text(text)
        # as of py 2.6.5 (and in the year 2010), the csv module seems to still
        # have troubles with unicode, thus we encode to utf-8 ...
        content = [line.encode('utf-8') for line in content]
        dialect = csv.Sniffer().sniff(content[0])
        reader = csv.reader(content, dialect)
        # ... and decode back to unicode
        rows = []
        for encoded_row in reader:
            row = []
            for encoded_cell in encoded_row:
                row.append(encoded_cell.decode('utf-8'))
            if row:
                rows.append(row)
        return self.build_dom_table(rows)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('text/csv'), type_moin_document)
