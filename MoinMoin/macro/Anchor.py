# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Anchor Macro to put an anchor at the place where it is used.
"""


from MoinMoin.util.tree import moin_page
from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, anchor=unicode):
        if not anchor:
            raise ValueError("Anchor: you need to specify an anchor name.")

        return moin_page.span(attrib={moin_page.id: anchor})

