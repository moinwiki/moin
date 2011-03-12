# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - PageSize Macro displays an ordered list with page sizes and names
"""

from flask import flaskg
from MoinMoin.storage.error import NoSuchRevisionError
from MoinMoin.macro._base import MacroNumberPageLinkListBase

class Macro(MacroNumberPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):
        sizes_pagenames = []
        for item in flaskg.storage.iteritems():
            try:
                rev = item.get_revision(-1)
            except NoSuchRevisionError:
                # XXX we currently also get user items, they have no revisions -
                # but in the end, they should not be readable by the user anyways
                continue
            sizes_pagenames.append((rev.size, item.name))
        sizes_pagenames.sort()
        sizes_pagenames.reverse()

        return self.create_number_pagelink_list(sizes_pagenames)

