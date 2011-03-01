# Copyright: 2005-2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Outputs the text verbatimly.
"""


from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, text=u''):
        return text

