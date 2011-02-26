"""
    MoinMoin - HighlighterList Macro

    A simple macro for displaying a table with list of available Pygments lexers.

    Usage: <<HighlighterList>>

    @copyright: 2009 MoinMoin:EugeneSyromyatnikov,
                2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import pygments.lexers

from MoinMoin.i18n import _, L_, N_
from MoinMoin.util.tree import moin_page
from MoinMoin.macro._base import MacroBlockBase
from MoinMoin.converter._table import TableMixin


class Macro(TableMixin, MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        request = self.request
        column_titles = [_('Lexer description'),
                         _('Lexer names'),
                         _('File patterns'),
                         _('Mimetypes'),
                        ]
        lexers = pygments.lexers.get_all_lexers()
        lexers = [[desc, ' '.join(names), ' '.join(patterns), ' '.join(mimetypes), ]
                  for desc, names, patterns, mimetypes in lexers]

        rows = [column_titles] + sorted(lexers)
        return self.build_dom_table(rows)

