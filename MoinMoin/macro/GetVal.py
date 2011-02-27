# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin GetVal macro - gets a value for a specified key from a dict.
"""


from flask import flaskg

from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, page=unicode, key=unicode):
        if page is None or key is None:
            raise ValueError("GetVal: you have to give pagename, key.")
        if not flaskg.user.may.read(page):
            raise ValueError("You don't have enough rights on this page")
        d = flaskg.dicts.dict(page)
        result = d.get(key, '')
        return result

