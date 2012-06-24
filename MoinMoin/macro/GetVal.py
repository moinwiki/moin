# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin GetVal macro - gets a value for a specified key from a dict.
"""


from flask import g as flaskg

from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        try:
            item_name = arguments[0]
            key = arguments[1]
        except IndexError:
            raise ValueError("GetVal: you have to give itemname, key.")
        if not flaskg.user.may.read(item_name):
            raise ValueError("You don't have enough rights on this page")
        d = flaskg.dicts[item_name]
        result = d.get(key, '')
        return result
