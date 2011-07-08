# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
PagenameList - list pages with names matching a string or regex

Note: PageList is a similar thing using the search engine.
"""


import re

from flask import g as flaskg

from MoinMoin.macro._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):
        # needle=u'', regex=False
        needle = arguments[0]
        try:
            regex = arguments[1] == 'True'
        except IndexError:
            regex = False
        re_flags = re.IGNORECASE
        if regex:
            try:
                needle_re = re.compile(needle, re_flags)
            except re.error as err:
                raise ValueError("Error in regex %r: %s" % (needle, err))
        else:
            needle_re = re.compile(re.escape(needle), re_flags)

        item_names = []
        for item in flaskg.storage.iteritems():
            if needle_re.search(item.name):
                item_names.append(item.name)

        item_names.sort()

        return self.create_pagelink_list(item_names, ordered=False)

