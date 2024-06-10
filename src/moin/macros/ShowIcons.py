# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Show all available icons that may be included in wiki item content
using the Icon macro:

    <<Icon(myicon.png)>>
"""


import os

from flask import url_for

from moin.utils.tree import html
from moin.macros._base import MacroBlockBase
from moin.i18n import _
from moin.converters._table import TableMixin


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        icon_dir = os.path.join(os.path.split(my_dir)[0], "static", "img", "icons")

        headings = (_("Markup"), _("Result"))
        rows = []
        with os.scandir(icon_dir) as files:
            for file in files:
                if not file.name.startswith(".") and file.is_file():
                    markup = f"<<Icon({file.name})>>"
                    src = url_for("static", filename="img/icons/" + file.name)
                    rows.append((markup, html.img(attrib={html.src: src, html.alt: file.name})))
        table = TableMixin()
        ret = table.build_dom_table(sorted(rows), head=headings)
        return ret
