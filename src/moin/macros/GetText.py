# Copyright: 2001 Juergen Hermann <jh@web.de>
# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Load I18N Text

This macro has the main purpose of supporting Help* page authors
to insert the texts that a user actually sees on his screen into
the description of the related features (which otherwise could
get very confusing).
"""


from moin.i18n import _
from moin.macros._base import MacroInlineBase


class Macro(MacroInlineBase):
    """Return a translation of args, or args as is"""

    def macro(self, content, arguments, page_url, alternative):
        translation = _(arguments[0])
        return translation
