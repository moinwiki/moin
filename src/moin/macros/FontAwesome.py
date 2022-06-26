# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Support use of Font Awesome fonts within wiki content.

Usage:
    <<FontAwesome(classes,color,size)>>
    <<FontAwesome(classes)>>
    <<FontAwesome(classes,,size)>>
    <<FontAwesome(classes,color)>>
Where:
    classes: one or more Font Awesome classes less leading "fa-", separated by " ": cog lg
    color: optional hex color code: #f00 or #ff0000
    size: optional int or float size in EM units (alternative to FA lg, 2x, 3x, 4x)
"""


from moin.utils.tree import moin_page
from moin.macros._base import MacroInlineBase


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        args = arguments[0] if arguments else ""
        if not args:
            raise ValueError("Missing font name")
        args = args.split(',')
        fonts = args[0].split()
        color = args[1].strip() if len(args) > 1 else ""
        size = args[2].strip() if len(args) > 2 else ""

        if color.startswith('#'):
            try:
                int(color[1:], 16)
                assert len(color) in (4, 7)
                color = 'color: {0}; '.format(color)
            except (ValueError, AssertionError):
                color = ""

        if size:
            try:
                s = float(size)
                assert s > 0.1
                assert s < 99
                size = 'font-size: {0}em;'.format(size)
            except (ValueError, AssertionError):
                size = ""

        style = color + size
        classes = []
        for font in fonts:
            f = font if font.startswith('fa-') or font == 'fa' else 'fa-' + font
            classes.append(f)
        if 'fa' not in classes:
            classes.insert(0, 'fa')
        classes = ' '.join(classes)

        attrib = {moin_page.class_: classes}
        if style:
            attrib[moin_page.style] = style
        return moin_page.span(attrib=attrib)
