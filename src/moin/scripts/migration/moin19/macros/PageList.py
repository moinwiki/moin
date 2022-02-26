""" Migration of PageList macro (moin1.9) to new ItemList macro (moin2)
"""

import re

from moin.scripts.migration.moin19 import macro_migration
from moin.utils.tree import html, moin_page, xlink, xinclude


CONTENT_TYPE_MACRO_FORMATTER = "x-moin/macro;name={}"
MACRO_NAME_PAGE_LIST = "PageList"


def convert_page_list_macro_to_item_list(node):
    """ Convert the given PageList macro node to an ItemList macro in-place

    The moin1.0 PageList macro used to pass all arguments to the FullSearch
    macro, so they were essentially all treated as regular expression search queries.
    After conversion to the ItemList macro, the argument will be a simple "regex" argument.

    Example conversions:

    | PageList macro (moin1.9)       | ItemList macro (moin2)           |
    |--------------------------------|----------------------------------|
    | <<PageList()>>                 | <<ItemList()>>                   |
    | <<PageList(SomeSubPage)>>      | <<ItemList(regex="SomeSubPage")>> |
    | <<PageList(regex:Rnd[^abc]+)>> | <<ItemList(regex="Rnd[^abc]+")>> |

    :param node: the DOM node matching the PageList macro content type
    :type node: emeraldtree.tree.Element
    """

    # content type
    new_content_type = CONTENT_TYPE_MACRO_FORMATTER.format('ItemList')
    node.set(moin_page.content_type, new_content_type)

    # arguments
    args_before = None
    args_after = ''
    for elem in node.iter_elements():
        if elem.tag.name == 'arguments':
            args_before = elem.text
    if args_before:
        # strip the "regex:" prefix if necessary
        args_intermediate = re.sub(r'^regex:', '', args_before)
        # wrap argument in new keyword argument "regex"
        args_after = 'regex="{}"'.format(args_intermediate)

    for elem in node.iter_elements():
        if elem.tag.name == 'arguments':
            elem.clear()
            elem.append(args_after)

    # 'alt' attribute
    new_alt = '<<ItemList({})>>'.format(args_after)
    node.set(moin_page.alt, new_alt)


macro_migration.register_macro_migration(
    CONTENT_TYPE_MACRO_FORMATTER.format(MACRO_NAME_PAGE_LIST),
    convert_page_list_macro_to_item_list
)
