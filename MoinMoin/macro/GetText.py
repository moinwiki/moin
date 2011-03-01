# Copyright: 2001 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Load I18N Text

    This macro has the main purpose of supporting Help* page authors
    to insert the texts that a user actually sees on his screen into
    the description of the related features (which otherwise could
    get very confusing).
"""


from MoinMoin.i18n import _, L_, N_
from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    """ Return a translation of args, or args as is """
    def macro(self, content, args, page_url, alt):
        translation = ' '.join(args.positional)
        translation = _(translation)
        return translation

