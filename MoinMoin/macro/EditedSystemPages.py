# Copyright: 2004 Nir Soffer <nirs@freeshell.org>
# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
EditedSystemPages - list system pages that has been edited in this wiki.
"""


from flask import flaskg

from MoinMoin.macro._base import MacroPageLinkListBase
from MoinMoin.items import IS_SYSITEM
from MoinMoin.storage.error import NoSuchRevisionError

class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):
        edited_sys_items = []
        for item in flaskg.storage.iteritems():
            try:
                rev = item.get_revision(-1)
            except NoSuchRevisionError:
                continue
            is_sysitem = rev.get(IS_SYSITEM, False)
            if is_sysitem:
                version = rev.get(SYSITEM_VERSION)
                if version is None:
                    # if we don't have the version, it was edited:
                    edited_sys_items.append(item.name)

        # Format as numbered list, sorted by item name
        edited_sys_items.sort()

        return self.create_pagelink_list(edited_sys_items, ordered=True)

