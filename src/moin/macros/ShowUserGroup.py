# Copyright: 2024 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Show contents of UserGroup attribute in metadata.
"""

from moin.macros._base import MacroBlockBase, fail_message
from moin.items import Item
from moin.constants.keys import USERGROUP
from moin.i18n import _


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        url = str(page_url.path)[1:]
        try:
            item = Item.create(url)
            return item.meta[USERGROUP]
        except KeyError:
            msg = _('ShowUserGroup macro failed - metadata lacks "usergroup" attribute.')
            return fail_message(msg)
