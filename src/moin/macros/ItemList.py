# Copyright: 2019 MoinMoin:KentWatsen
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
ItemList - generates a list of links to an item's subitems.

  Only items the user has access to are queryable.  If the specified item
  has no subitems matching the filter, which may be due to filters or
  access controls, the macro displays a list (to match context) containing a
  single item with the message no matching items were found.

Parameters:

    item: the wiki item to select.  If no item is specified, then the
          current item is used.

    startswith: the substring the item's descendants must begin with.
                If no value is specified, then no startswith-filtering
                is applied.

    regex: a regular expression the item's descendants must match.
           If no value is specified, then no regex-filtering is applied.

    ordered: Should the list be ordered or unordered list (<ol> or <ul>)?
             Options:
               False : Display list as an unordered list.  (default)
               True  : Display list as an ordered list.

    skiptag: a tag name, items with tag will be skipped

    tag: only include items that have been tagged with this name

    display: How should the link be displayed?

        Options:
            FullPath  : The full item path (default)

            ChildPath : The last component of the FullPath, including the '/'

            ChildName : ChildPath, but minus the leading '/'

            UnCameled : ChildName, but with a space ' ' character between
                        blocks of lowercase characters or numbers and an
                        uppercase character.

            ItemTitle : Use the title from the first header in the linked item

Notes:

    All parameter values must be bracketed by matching quotes.  Single quotes
    or double quotes are okay.

    The "startswith" and "regex" filters may be used together.  The "startswith"
    filter is more efficient, since it's passed into the underlying database query,
    whereas the "regex" filter is applied to the results returned from the database.

    This is a block-level macro; do not embed it in a paragraph.

Examples:
    <<ItemList>>
    <<ItemList(item="")>>
    <<ItemList(item="Foo/Bar", ordered='True', display="UnCameled")>>
"""

import re
from flask import request
from flask import g as flaskg
from moin.i18n import _
from moin.utils.interwiki import split_fqname
from moin.macros._base import MacroPageLinkListBase, get_item_names, fail_message
from moin.converters._args_wiki import parse as parse_arguments


class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):

        # defaults
        item = None
        startswith = ""
        regex = None
        ordered = False
        display = "FullPath"
        skiptag = ""
        tag = ""

        # process arguments
        if arguments:
            args = parse_arguments(arguments[0])

            for key, val in args.items():
                if not key and val:
                    err_msg = _(
                        'ItemList macro: Argument "{arg}" does not follow <key>=<val> format '
                        "(arguments, if more than one, must be comma-separated)."
                    ).format(arg=val)
                    return fail_message(err_msg, alternative)
                if key == "item":
                    item = val
                elif key == "startswith":
                    startswith = val
                elif key == "regex":
                    regex = val
                elif key == "ordered":
                    if val == "False":
                        ordered = False
                    elif val == "True":
                        ordered = True
                    else:
                        err_msg = _('The value for "{key}" must be "True" or "False", got "{val}".').format(
                            key=key, val=val
                        )
                        return fail_message(err_msg, alternative)
                elif key == "display":
                    display = val  # let 'create_pagelink_list' throw an exception if needed
                elif key == "skiptag":
                    skiptag = val
                elif key == "tag":
                    tag = val
                else:
                    err_msg = _('Unrecognized key "{key}".').format(key=key)
                    return fail_message(err_msg, alternative)

        # use curr item if not specified
        if item is None:
            item = request.path[1:]
            if item.startswith("+modify/"):
                item = item.split("/", 1)[1]

        if item == "/":
            item = ""
        # verify item exists and current user has read permission
        elif item != "":
            if not flaskg.storage.get_item(short=True, **(split_fqname(item).query)):
                err_msg = _("Item does not exist or read access blocked by ACLs: {0}").format(item)
                return fail_message(err_msg, alternative)

        if regex:
            try:
                re.compile(regex, re.IGNORECASE)
            except re.error as err:
                err_msg = _("Error in regex {0!r}: {1}").format(regex, err)
                return fail_message(err_msg, alternative)

        children = get_item_names(item, startswith=startswith, skiptag=skiptag, tag=tag, regex=regex)

        if not children:
            return fail_message(_("No matching items were found"), alternative, severity="attention")

        return self.create_pagelink_list(children, alternative, ordered, display)
