# Copyright: 2007-2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Outputs the interwiki map.
"""


from flask import current_app as app

from MoinMoin.util.tree import moin_page, xlink
from MoinMoin.util.interwiki import join_wiki
from MoinMoin.macro._base import MacroBlockBase

class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        iwlist = app.cfg.interwiki_map.items()
        iwlist.sort()

        iw_list = moin_page.list()
        for tag, url in iwlist:
            href = join_wiki(url, 'RecentChanges')
            link = moin_page.a(attrib={xlink.href: href}, children=[tag])
            label = moin_page.code(children=[link])
            iw_item_label = moin_page.list_item_label(children=[label])
            if '$PAGE' not in url:
                link = moin_page.a(attrib={xlink.href: url}, children=[url])
            else:
                link = url
            body = moin_page.code(children=[link])
            iw_item_body = moin_page.list_item_body(children=[body])
            iw_item = moin_page.list_item(children=[iw_item_label, iw_item_body])
            iw_list.append(iw_item)
        return iw_list

