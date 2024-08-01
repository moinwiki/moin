# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create link to start a SlideShow for the current item
"""

from moin.i18n import _
from moin.utils.tree import moin_page, xlink
from moin.macros._base import MacroInlineBase


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        attrib = {moin_page.class_: "fa-regular fa-circle-play"}
        children = [moin_page.span(attrib=attrib), _(" Start SlideShow")]
        result = moin_page.a(attrib={xlink.href: f"/+slideshow{page_url.path}"}, children=children)
        return result
