# Copyright:  2016 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
HighlighterList - display a list of Pygments lexers

Usage: <<HighlighterList>>
"""

import pygments

from moin.macros._base import MacroBlockBase
from moin.i18n import _
from moin.converters._table import TableMixin


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        headings = (_("Lexer Name"), _("Lexer Aliases"), _("File Patterns"), _("Mimetypes"))
        rows = list(pygments.lexers.get_all_lexers())
        rows.sort(key=lambda t: tuple(t[0].lower()))
        # Prevent traceback in converters/highlight.py when
        # "..?regex=high" is appended to a Pygments Highlighter List
        # A row above consists of [str, tuple, tuple, tuple] where singular tuples contain strings
        pretty_rows = [[str(col) for col in row] for row in rows]
        table = TableMixin()
        ret = table.build_dom_table(pretty_rows, head=headings, cls="moin-sortable")
        return ret
