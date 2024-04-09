# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - table data to DOM conversion support
"""

from moin.utils.tree import moin_page
from emeraldtree import ElementTree as ET

WORDBREAK_LEN = 30


class TableMixin:
    """
    Mixin to support building a DOM table.
    """

    def add_numeric_class(self, cell, table_cell):
        """
        Add numeric class attribute if cell is numeric.
        """
        try:
            float(cell)
        except (ValueError, TypeError):
            pass
        else:
            table_cell.attrib[moin_page("class")] = "moin-integer"

    def build_dom_table(self, rows, head=None, cls=None):
        """
        Build a DOM table with data from <rows>.
        """
        table = moin_page.table()
        if cls is not None:
            table.attrib[moin_page("class")] = cls
        if head is not None:
            table_head = moin_page.table_header()
            table_row = moin_page.table_row()
            for idx, cell in enumerate(head):
                table_cell = moin_page.table_cell(children=[cell])
                if rows and len(rows[0]) == len(head):
                    # add "align: right" to heading cell if cell in first data row is numeric
                    self.add_numeric_class(rows[0][idx], table_cell)
                table_row.append(table_cell)
            table_head.append(table_row)
            table.append(table_head)
        table_body = moin_page.table_body()
        for row in rows:
            table_row = moin_page.table_row()
            for cell in row:
                if (
                    isinstance(cell, ET.Node)
                    and len(cell)
                    and isinstance(cell[0], str)
                    and len(cell[0].split()) == 1
                    and len(cell[0]) > WORDBREAK_LEN
                ):
                    # avoid destroying table layout by applying special styling to cells with long file name hyperlinks
                    table_cell = moin_page.table_cell(children=[cell], attrib={moin_page.class_: "moin-wordbreak"})
                elif isinstance(cell, ET.Node):
                    table_cell = moin_page.table_cell(children=[cell])
                else:
                    table_cell = moin_page.table_cell(children=[cell])
                    self.add_numeric_class(cell, table_cell)
                table_row.append(table_cell)
            table_body.append(table_row)
        table.append(table_body)
        return table
