# Copyright: 2002 Juergen Hermann <jh@web.de>
# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - PageSize Macro displays an ordered list with page sizes and names
"""


from MoinMoin.Page import Page
from MoinMoin.macro._base import MacroNumberPageLinkListBase

class Macro(MacroNumberPageLinkListBase):
    def macro(self):
        # get list of pages and their objects
        pages = self.request.rootpage.getPageList()

        # get sizes and sort them
        sizes_pagenames = [(Page(self.request, name).size(), name)
                for name, page in pages.items()]
        sizes_pagenames.sort()
        sizes_pagenames.reverse()

        return self.create_number_pagelink_list(sizes_pagenames)

