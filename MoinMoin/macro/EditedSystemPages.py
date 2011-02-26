"""
    EditedSystemPages - list system pages that has been edited in this wiki.

    @copyright: 2004 Nir Soffer <nirs@freeshell.org>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from flask import flaskg

from MoinMoin.Page import Page
from MoinMoin.macro._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self):
        from MoinMoin.Page import Page
        from MoinMoin.items import IS_SYSITEM

        # Get item list for current user (use this as admin), filter
        # items that are sysitems
        def filterfn(name):
            item = flaskg.storage.get_item(name)
            try:
                return item.get_revision(-1)[IS_SYSITEM]
            except KeyError:
                return False

        # Get page filtered page list. We don't need to filter by
        # exists, because our filter check this already.
        pagenames = list(self.request.rootpage.getPageList(filter=filterfn, exists=0))

        # Format as numbered list, sorted by page name
        pagenames.sort()

        return self.create_pagelink_list(pagenames, ordered=True)

