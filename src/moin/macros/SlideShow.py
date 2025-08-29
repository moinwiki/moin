# Copyright: 2024-2025 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create a link to start a slide show for the current item.
"""

from flask import url_for
from moin.i18n import _
from moin.utils.tree import moin_page, xlink
from moin.macros._base import MacroInlineBase


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        attrib = {moin_page.class_: "fa-regular fa-circle-play"}
        # Visible label for the slide show link
        children = [moin_page.span(attrib=attrib), _(" Start Slide Show")]
        url = url_for("frontend.slide_item", item_name=page_url.path[1:])
        result = moin_page.a(attrib={xlink.href: url, moin_page.class_: "moin-no-print"}, children=children)
        return result
