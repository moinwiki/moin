# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Support the use of icons within wiki content.

Unlike Moin 1.x, Moin 2 has a single icon directory rather than one per theme.
Moin 1.x passed predefined alt text, width, and height within the <img> tag;
Moin 2 assumes an error if an icon is not rendered (alt text displayed in red)
and relies on the client browser to render the image based on its size.
"""


from flask import url_for

from moin.utils.tree import html
from moin.macros._base import MacroInlineBase, fail_message
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        icon = arguments[0] if arguments else ""
        if not icon:
            msg = _("Icon macro failed due to missing icon name.")
            return fail_message(msg, alternative)
        src = url_for("static", filename="img/icons/" + icon)
        reason = _("Icon not rendered (invalid name)")
        alt = f"<<Icon({icon})>> - {reason}"
        return html.img(attrib={html.src: src, html.alt: alt, html.class_: "moin-icon-macro"})
