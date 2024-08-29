# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create link to start a SlideShow for the current item
"""

from flask import url_for
from moin.i18n import _
from moin.utils.tree import moin_page, xlink
from moin.macros._base import MacroInlineBase


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        attrib = {moin_page.class_: "fa-regular fa-circle-play"}
        children = [moin_page.span(attrib=attrib), _(" Start SlideShow")]
        url = url_for("frontend.slide_item", item_name=page_url.path[1:])
        result = moin_page.a(attrib={xlink.href: url}, children=children)
        return result
