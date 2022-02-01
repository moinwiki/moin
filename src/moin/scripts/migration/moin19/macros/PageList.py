""" Migration of PageList macro (moin1.9) to new ItemList macro (moin2)
"""

from moin.scripts.migration.moin19 import macro_migration
from moin.utils.tree import html, moin_page, xlink, xinclude


CONTENT_TYPE_MACRO_FORMATTER="x-moin/macro;name={}"
MACRO_NAME_PAGE_LIST = "PageList"

def convert_page_list_macro_to_item_list(node):
    """ Convert the given PageList macro node to an ItemList macro in-place

    Depending on the argument of the moin1.0 PageList macro, the new
    ItemList macro will have a simple "item" argument or a "regex" argument.

    Example conversions:

    | PageList macro (moin1.9)              | ItemList macro (moin2)                      |
    |---------------------------------------|---------------------------------------------|
    | <<PageList()>>                        | <<ItemList()>>                              |
    | <<PageList(MyInterestingSubPage)>>    | <<ItemList(item="MyInterestingSubPage")>>   |
    | <<PageList(regex:RandomItem[^abc]+)>> | <<ItemList(regex="RandomItem[^abc]+")>>     |

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
        if args_before.startswith('regex:'):
            # strip the "regex:" prefix and convert to keyword argument "regex"
            args_after = 'regex="{}"'.format(args_before[6:])
        else:
            # wrap unnamed arguments in new keyword argument "item"
            args_after = 'item="{}"'.format(args_before)

    for elem in node.iter_elements():
        if elem.tag.name == 'arguments':
            elem.clear()
            elem.append(args_after)

    # 'alt' attribute
    new_alt = '<<ItemList({})>'.format(args_after)
    node.set(moin_page.alt, new_alt)


macro_migration.register_macro_migration(
    CONTENT_TYPE_MACRO_FORMATTER.format(MACRO_NAME_PAGE_LIST),
    convert_page_list_macro_to_item_list
)
