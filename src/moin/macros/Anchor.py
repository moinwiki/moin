# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - The Anchor Macro is used to create an anchor comprised of a span tag with
an id attribute. Per HTML5 the id must be at least 1 character with no space characters.
"""

from moin.utils.tree import moin_page
from moin.macros._base import MacroInlineBase, fail_message
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        if not arguments:
            msg = _("Anchor macro failed - missing argument.")
            return fail_message(msg, alternative)

        if len(arguments) > 1:
            msg = _("Anchor macro failed - only 1 argument allowed.")
            return fail_message(msg, alternative)

        anchor = arguments[0]
        if " " in anchor:
            msg = _("Anchor macro failed - space is not allowed in anchors.")
            return fail_message(msg, alternative)

        return moin_page.span(attrib={moin_page.id: anchor})
