# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Support use of icons within wiki content.

Unlike moin 1.x, moin 2 has one icon directory, not one per theme.
Moin 1.x passed predefined alt text, width and height within the img tag;
moin 2 assumes an error if icon is not rendered (alt text displayed in red font)
and relies on client browser to render image based on its size.
"""


from flask import url_for

from MoinMoin.util.tree import html
from MoinMoin.macro._base import MacroInlineBase
from MoinMoin.i18n import _, L_, N_


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        icon = arguments[0] if arguments else ''
        if not icon:
            raise ValueError("Missing icon name")
        src = url_for('static', filename='img/icons/' + icon)
        reason = _('Icon not rendered, verify name is valid')
        alt = '<<Icon({0})>> - {1}'.format(icon, reason)
        return html.img(attrib={html.src: src, html.alt: alt, html.class_: 'moin-icon-macro'})
