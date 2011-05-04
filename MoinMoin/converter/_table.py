# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - table data to DOM conversion support
"""


from __future__ import absolute_import, division

from MoinMoin.util.tree import moin_page

class TableMixin(object):
    """
    Mixin to support building a DOM table.
    """
    def build_dom_table(self, rows):
        """
        Build a DOM table with data from <rows>.
        """
        table_body = moin_page.table_body()
        for row in rows:
            table_row = moin_page.table_row()
            for cell in row:
                table_cell = moin_page.table_cell(children=[cell, ])
                table_row.append(table_cell)
            table_body.append(table_row)
        return moin_page.table(children=[table_body, ])

