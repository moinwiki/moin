# -*- coding: iso-8859-1 -*-
"""
    PagenameList - list pages with names matching a string or regex

    Note: PageList is a similar thing using the search engine.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import re

from MoinMoin.macro._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self, needle=u'', regex=False):
        re_flags = re.IGNORECASE
        if regex:
            try:
                needle_re = re.compile(needle, re_flags)
            except re.error, err:
                raise ValueError("Error in regex %r: %s" % (needle, err))
        else:
            needle_re = re.compile(re.escape(needle), re_flags)

        # Get page list readable by current user, filtered by needle
        pagenames = self.request.rootpage.getPageList(filter=needle_re.search)
        pagenames.sort()

        return self.create_pagelink_list(pagenames, ordered=False)

