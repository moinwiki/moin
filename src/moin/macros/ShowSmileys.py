# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Show all available smileys that may be included in wiki item content
"""

from flask import url_for

from moin.utils.tree import html
from moin.macros._base import MacroBlockBase
from moin.i18n import _
from moin.converters._table import TableMixin
from moin.converters.smiley import Converter


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        smileys = Converter.smileys
        headings = (_("Markup"), _("Result"), _("Name"))
        rows = []
        for key in smileys.keys():
            icon_name = smileys[key]
            src = url_for("static", filename="img/icons/" + icon_name + ".png")
            rows.append((key, html.img(attrib={html.src: src, html.alt: icon_name}), icon_name))
        table = TableMixin()
        ret = table.build_dom_table(rows, head=headings)
        return ret
