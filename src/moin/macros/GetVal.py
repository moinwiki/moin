# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin GetVal macro - gets a value for a specified key from a dict.
"""


from flask import g as flaskg

from moin.macros._base import MacroInlineBase, fail_message
from moin.datastructures.backends import DictDoesNotExistError
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        try:
            args = arguments[0].split(",")
            assert len(args) == 2
            item_name = args[0].strip()
            key = args[1].strip()
        except (IndexError, AssertionError):
            err_msg = _("Invalid parameters, try <<GetVal(DictName, key)>>")
            return fail_message(err_msg, alternative)

        if not flaskg.user.may.read(str(item_name)):
            err_msg = _("Permission to read was denied: {item_name}").format(item_name=item_name)
            return fail_message(err_msg, alternative)

        try:
            d = flaskg.dicts[item_name]
        except DictDoesNotExistError:
            err_msg = _("WikiDict not found: {item_name}").format(item_name=item_name)
            return fail_message(err_msg, alternative)

        result = d.get(key, "")
        if not result:
            err_msg = _("Macro is invalid, {item_name} is missing key: {key_name}").format(
                item_name=item_name, key_name=key
            )
            return fail_message(err_msg, alternative)
        return result
