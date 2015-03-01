# Copyright: 2015 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.text_csv_in
"""


import re

from MoinMoin.util.tree import moin_page, xlink, html, xinclude

from ..text_csv_in import Converter


class TestConverter(object):
    namespaces = {
        moin_page: '',
        xlink: 'xlink',
        html: 'xhtml',
        xinclude: 'xinclude',
    }

    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv = Converter()

    def test_csv(self):
        data = [
            # first row not recognized as a header by Python csv module
            (u'Head A,Head B\na,bb\nccc,dddd',
                '<page><body><table><table-body><table-row><table-cell>Head A</table-cell><table-cell>Head B</table-cell></table-row><table-row><table-cell>a</table-cell><table-cell>bb</table-cell></table-row><table-row><table-cell>ccc</table-cell><table-cell>dddd</table-cell></table-row></table-body></table></body></page>'),
            # first row recognized as header
            (u'Head A;Head B\n1;2\n3;4',
                '<page><body><table class="moin-sortable"><table-header><table-row><table-cell class="moin-integer">Head A</table-cell><table-cell class="moin-integer">Head B</table-cell></table-row></table-header><table-body><table-row><table-cell class="moin-integer">1</table-cell><table-cell class="moin-integer">2</table-cell></table-row><table-row><table-cell class="moin-integer">3</table-cell><table-cell class="moin-integer">4</table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}):
        out = self.conv(input, 'text/csv;charset=utf-8', **args)
        assert self.serialize(out) == output
