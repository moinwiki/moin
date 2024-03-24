# Copyright: 2024 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create a H1 look-alike that will not be included in TableOfContents.

<<PageTitle(My Page Title)>>
"""

from moin.utils.tree import html
from moin.macros._base import MacroBlockBase


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        ret = html.div(attrib={html.class_: "moin-pagetitle"}, children=arguments[0])
        return ret
