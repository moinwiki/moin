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

    startswith: the substring the item's descendents must begin with.
                If no value is specified, then no startswith-filtering
                is applied.

    regex: a regular expresssion the item's descendents must match.
           If no value is specified, then no regex-filtering is applied.

    ordered: Should the list be ordered or unordered list (<ol> or <ul>)?
             Options:
               False : Display list as an unordered list.  (default)
               True  : Display list as an ordered list.

    skiptag: a tag name, items with tag will be skipped

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

    All parameter values must be bracketed by matching quotes.  Singlequote
    or doublequotes are okay.

    The "startswith" and "regex" filters may be used together.  The "startswith"
    filter is more efficient, since it's passed into the underlyng database query,
    whereas the "regex" filter is applied on the results returned from the database.

    This is a block level macro, do not embed in a paragraph.

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


class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):

        # defaults
        item = None
        startswith = ""
        regex = None
        ordered = False
        display = "FullPath"
        skiptag = ""

        # process input
        args = []
        if arguments:
            args = arguments[0].split(",")
        for arg in args:
            try:
                key, val = (x.strip() for x in arg.split("="))
            except ValueError:
                err_msg = _(
                    'ItemList macro: Argument "{arg}" does not follow <key>=<val> format '
                    "(arguments, if more than one, must be comma-separated)."
                ).format(arg=arg)
                return fail_message(err_msg, alternative)

            if len(val) < 2 or (val[0] != "'" and val[0] != '"') and val[-1] != val[0]:
                err_msg = _("The key's value must be bracketed by matching quotes.")
                return fail_message(err_msg, alternative)

            val = val[1:-1]  # strip out the doublequote characters

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
                    err_msg = _('The value must be "True" or "False". (got "{val}")').format(val=val)
                    return fail_message(err_msg, alternative)

            elif key == "display":
                display = val  # let 'create_pagelink_list' throw an exception if needed
            elif key == "skiptag":
                skiptag = val
            else:
                err_msg = _('Unrecognized key "{key}".').format(key=key)
                return fail_message(err_msg, alternative)

        # use curr item if not specified
        if item is None:
            item = request.path[1:]
            if item.startswith("+modify/"):
                item = item.split("/", 1)[1]

        # verify item exists and current user has read permission
        if item != "":
            if not flaskg.storage.get_item(**(split_fqname(item).query)):
                err_msg = _("Item does not exist or read access blocked by ACLs: {0}").format(item)
                return fail_message(err_msg, alternative)

        # process subitems
        children = get_item_names(item, startswith=startswith, skiptag=skiptag)
        if regex:
            try:
                regex_re = re.compile(regex, re.IGNORECASE)
            except re.error as err:
                err_msg = _("Error in regex {0!r}: {1}").format(regex, err)
                return fail_message(err_msg, alternative)

            newlist = []
            for child in children:
                if regex_re.search(child.fullname):
                    newlist.append(child)
            children = newlist
        if not children:
            return fail_message(_("No matching items were found"), alternative, severity="attention")

        return self.create_pagelink_list(children, alternative, ordered, display)
