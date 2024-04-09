# Copyright: 2000 Juergen Hermann <jh@web.de>
# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - RandomItem Macro displays one or multiple random item links.

TODO: add mimetype param and only show items matching this mimetype
"""

import random

from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.items import Item
from moin.macros._base import MacroPageLinkListBase, get_item_names
from moin.storage.middleware.protecting import AccessDenied

random.seed()


class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):
        if arguments:
            item_count = int(arguments[0])
        else:
            item_count = 1

        all_item_names = get_item_names()

        # Now select random item from the full list, and if it exists and
        # we can read it, save.
        random_item_names = []
        found = 0
        while found < item_count and all_item_names:
            # Take one random item from the list
            item_name = random.choice(all_item_names)
            all_item_names.remove(item_name)

            # Filter out items the user may not read.
            try:
                Item.create(item_name.value)
                random_item_names.append(item_name.value)
                found += 1
            except AccessDenied:
                pass

        if not random_item_names:
            return

        random_item_names.sort()

        result = moin_page.span()
        for name in random_item_names:
            link = str(Iri(scheme="wiki", authority="", path="/" + name))
            result.append(moin_page.a(attrib={xlink.href: link}, children=[name]))
            result.append(", ")

        del result[-1]  # kill last comma
        return result
