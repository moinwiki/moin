# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
TitleIndex - generates a list of links for the namespace of the current item, grouped by initials

Parameters:
    None

Usage:
    <<TitleIndex>>
"""

from moin.macros._base import MacroMultiLinkListBase, get_item_names, fail_message
from moin.i18n import _
from moin.utils.tree import moin_page
from moin.utils.interwiki import split_fqname


class Macro(MacroMultiLinkListBase):
    def macro(self, content, arguments, page_url, alternative):
        # get namespace of current item
        namespace = split_fqname(str(page_url.path)).namespace

        if arguments:
            err_msg = _("TitleList macro does not support any arguments.")
            return fail_message(err_msg, alternative)

        children = get_item_names(namespace)
        if not children:
            empty_list = moin_page.list(attrib={moin_page.item_label_generate: "unordered"})
            item_body = moin_page.list_item_body(children=[_("<TitleList macro: No matching items were found.>")])
            empty_list.append(moin_page.list_item(children=[item_body]))
            return empty_list

        return self.create_multi_pagelink_list(children, namespace)
