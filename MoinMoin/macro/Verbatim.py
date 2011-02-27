"""
    Outputs the text verbatimly.

    @copyright: 2005-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, text=u''):
        return text

