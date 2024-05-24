# Copyright: 2017-2023 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Support use of Font Awesome fonts within wiki content.

Usage:
    <<FontAwesome(classes,color,size)>>
    <<FontAwesome(classes)>>
    <<FontAwesome(classes,,size)>>
    <<FontAwesome(classes,color)>>

    <<FontAwesome(regular thumbs-up,red,2)>>

Where:
    classes: one or more Font Awesome classes less leading "fa-", separated by " ".
    color: optional hex color code: #f00 or #ff0000 or HTML color name
    size: optional int or float size in EM units
"""


from moin.utils.tree import moin_page
from moin.macros._base import MacroInlineBase, fail_message
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        if not arguments:
            err_msg = _("Missing font name, syntax is <<FontAwesome(name,color,size)>>")
            return fail_message(err_msg, alternative)

        args = arguments[0].split(",")
        fonts = args[0].split()
        color = args[1].strip() if len(args) > 1 else ""
        size = args[2].strip() if len(args) > 2 else ""

        if color.startswith("#"):
            try:
                int(color[1:], 16)
                assert len(color) in (4, 7)
                color = f"color: {color}; "
            except (ValueError, AssertionError):
                color = ""
        else:
            color = f"color: {color}; " if color.isalpha() else ""

        if size:
            try:
                s = float(size)
                assert s > 0.1
                assert s < 99
                size = f"font-size: {size}em;"
            except (ValueError, AssertionError):
                size = ""

        style = color + size
        classes = []
        for font in fonts:
            f = font if font.startswith("fa-") else "fa-" + font
            classes.append(f)
        if "fa-solid" not in classes and "fa-regular" not in classes and "fa-brands" not in classes:
            classes.insert(0, "fa-solid")
        if "fa-spin-reverse" in classes and "fa-spin" not in classes:
            classes.insert(0, "fa-spin")
        classes = " ".join(classes)

        attrib = {moin_page.class_: classes}
        if style:
            attrib[moin_page.style] = style
        return moin_page.span(attrib=attrib)
