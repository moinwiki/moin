# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin GetVal macro - gets a value for a specified key from a dict.
"""


from flask import g as flaskg

from MoinMoin.macro._base import MacroInlineBase
from MoinMoin.datastruct.backends import DictDoesNotExistError
from MoinMoin.i18n import _, L_, N_


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        try:
            args = arguments[0].split(',')
            assert len(args) == 2
            item_name = args[0].strip()
            key = args[1].strip()
        except (IndexError, AssertionError):
            raise ValueError(_("GetVal: invalid parameters, try <<GetVal(DictName, key)>>"))
        if not flaskg.user.may.read(unicode(item_name)):
            raise ValueError(_("GetVal: permission to read denied: ") + item_name)
        try:
            d = flaskg.dicts[item_name]
        except DictDoesNotExistError:
            raise ValueError(_("GetVal: dict not found: ") + item_name)
        result = d.get(key, '')
        return result
