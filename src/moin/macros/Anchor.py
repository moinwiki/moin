# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Anchor macro.

Creates an anchor as a span tag with an id attribute. Per HTML5, the id must be at least one character and contain no spaces.
"""

from moin.utils.tree import moin_page
from moin.macros._base import MacroInlineBase, fail_message
from moin.i18n import _


class Macro(MacroInlineBase):
    def macro(self, content, arguments, page_url, alternative):
        if not arguments:
            msg = _("Anchor macro failed: missing anchor name.")
            return fail_message(msg, alternative)

        if len(arguments) > 1:
            msg = _("Anchor macro failed: only one argument is allowed.")
            return fail_message(msg, alternative)

        anchor = arguments[0]
        if " " in anchor:
            msg = _("Anchor macro failed: spaces are not allowed in anchors.")
            return fail_message(msg, alternative)

        return moin_page.span(attrib={moin_page.id: anchor})
