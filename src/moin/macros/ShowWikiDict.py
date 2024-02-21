# Copyright: 2024 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Show contents of WikiDict attribute in metadata.
"""

from moin.macros._base import MacroBlockBase, fail_message
from moin.items import Item
from moin.constants.keys import WIKIDICT
from moin.i18n import _


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        url = str(page_url.path)[1:]
        try:
            item = Item.create(url)
            return item.meta[WIKIDICT]
        except KeyError:
            msg = _('ShowWikiDict macro failed - metadata lacks "wikidict" attribute.')
            return fail_message(msg)
