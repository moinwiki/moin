# Copyright:  2016 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
HighlighterList - display a list of Pygments lexers

Usage: <<HighlighterList>>
"""

import pygments

from moin.macros._base import MacroBlockBase
from moin.i18n import _, L_, N_
from moin.converters._table import TableMixin


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        headings = (_('Lexer Name'),
                    _('Lexer Aliases'),
                    _('File Patterns'),
                    _('Mimetypes'),
                   )
        rows = list(pygments.lexers.get_all_lexers())
        rows.sort(key=lambda t: tuple(t[0].lower()))
        table = TableMixin()
        ret = table.build_dom_table(rows, head=headings, cls='moin-sortable')
        return ret
