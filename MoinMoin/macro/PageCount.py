"""
    Outputs the page count of the wiki.

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @copyright: 2008 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.macro._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, exists=None):
        """ Return number of pages readable by current user

        Return either an exact count (slow!) or fast count including deleted pages.

        TODO: make macro syntax more sane
        """
        request = self.request

        # Check input
        only_existing = False
        if exists == u'exists':
            only_existing = True
        elif exists:
            raise ValueError("Wrong argument: %r" % exists)

        count = request.rootpage.getPageCount(exists=only_existing)
        return "%d" % count

