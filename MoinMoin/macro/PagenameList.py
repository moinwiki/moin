# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    PagenameList - list pages with names matching a string or regex

    Note: PageList is a similar thing using the search engine.
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

