# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Show all available icons that may be included in wiki item content
using the Icon macro:

    <<Icon(myicon.png)>>
"""


import os
from os import listdir
from os.path import isfile, join

from flask import url_for

from moin.utils.tree import html
from moin.macros._base import MacroBlockBase
from moin.i18n import _
from moin.converters._table import TableMixin


class Macro(MacroBlockBase):
    def macro(self, content, arguments, page_url, alternative):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        icon_dir = os.path.join(os.path.split(my_dir)[0], 'static', 'img', 'icons')

        headings = (_('Markup'), _('Result'))
        files = [f for f in listdir(icon_dir) if isfile(join(icon_dir, f))]
        rows = []
        for filename in files:
            markup = '<<Icon({0})>>'.format(filename)
            src = url_for('static', filename='img/icons/' + filename)
            # TODO: add alt attribute for img and add a macro test module
            # reason = _('Icon not rendered, verify name is valid')
            # alt = '<<Icon({0})>> - {1}'.format(filename, reason)
            rows.append((markup, html.img(attrib={html.src: src, html.alt: filename})))
        table = TableMixin()
        ret = table.build_dom_table(rows, head=headings)
        return ret
