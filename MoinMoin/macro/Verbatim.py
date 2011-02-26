"""
    Outputs the text verbatimly.

    @copyright: 2005-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, text=u''):
        return text

