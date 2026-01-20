# Copyright: 2002-2004 Juergen Hermann <jh@web.de>
# Copyright: 2002 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - RandomQuote macro selects a random quote from FortuneCookies or a given wiki item.

    Usage:
        <<RandomQuote()>>
        <<RandomQuote(WikiTips)>>

    Comments:
        It will look for list delimiters in the item in question.
        It will ignore anything that is not in an "*" list.
"""

import random

from moin.constants.keys import NAME_EXACT
from moin.items import Item
from moin.i18n import _
from moin.constants.itemtypes import ITEMTYPE_NONEXISTENT
from moin.converters._util import decode_data
from moin.converters import default_registry as reg
from moin.macros._base import MacroInlineBase, fail_message, valid_item_name
from moin.utils.mime import Type, type_moin_document

from moin.utils.names import get_fqname, split_fqname

random.seed()


class Macro(MacroInlineBase):
    """Return a random quote from FortuneCookies or a given wiki item"""

    def macro(self, content, arguments, page_url, alternative):
        item_name = arguments[0] if arguments else "FortuneCookies"
        if item_name[0] in ['"', "'"] and item_name[-1] in ['"', "'"]:  # remove quotes
            item_name = item_name[1:-1]
        if not valid_item_name(item_name):
            err_msg = _("Invalid value given for item name: {0}").format(item_name)
            return fail_message(err_msg, alternative)

        # use same namespace as current item
        namespace = split_fqname(str(page_url.path)).namespace
        if not item_name.startswith(f"{namespace}/"):
            item_name = get_fqname(item_name, NAME_EXACT, namespace)

        # get the item with the list of quotes
        item = Item.create(item_name)
        if item.itemtype == ITEMTYPE_NONEXISTENT:
            err_msg = _("Item does not exist or read access blocked by ACLs: {0}").format(item_name)
            return fail_message(err_msg, alternative)
        data = decode_data(item.content.data, item.contenttype)

        # select lines looking like a list item
        quotes = data.splitlines()
        quotes = [quote.strip() for quote in quotes]
        quotes = [quote[2:] for quote in quotes if quote.startswith("* ")]
        if not quotes:
            err_msg = _("No quotes found in {0}").format(item_name)
            return fail_message(err_msg, alternative)

        result = random.choice(quotes)
        # quote may use some sort of markup, convert it to dom
        input_conv = reg.get(Type(item.contenttype), type_moin_document, includes="expandall")
        if not input_conv:
            raise TypeError(f"We cannot handle the conversion from {item.contenttype} to the DOM tree")
        return input_conv(result)
