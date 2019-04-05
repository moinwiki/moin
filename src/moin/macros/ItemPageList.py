# Copyright: 2019 MoinMoin:KentWatsen
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
ItemPageList - Replaced by a list of links to a specified page's descendents.

  Only items the user has access to are queryable.  If the specified item
  does not exist, then it displays "Specified item does not exist.".

  Only child pages the user has access to are returned.  If there are no
  child pages to return, then it displays "Specified item has no children.".

Parameters:

    item: the wiki item to select.  If no item is specified, then the
          current page is used. 

    startswith: the substring the item's descendents must begin with.
                If no value is specified, then no startswith-filtering
                is applied.

    regex: a regular expresssion the item's descendents must match.
           If no value is specified, then no regex-filtering is applied.

    ordered: Should the list be ordered or unordered list (<ol> or <ul>)?
             Options:
               False : Display list as an unordered list.  (default)
               True  : Display list as an ordered list.

    display: How should the link be displayed?

        Options:
            FullPath  : The full page path (default)

            ChildPath : The last component of the FullPath, including the '/'

            ChildName : ChildPath, but minus the leading '/'

            UnCameled : ChildName, but with a space ' ' character between
                        blocks of lowercase characters or numbers and an
                        uppercase character.

            PageTitle : Use the title from the first header in the linked
                        page [*** NOT IMPLEMENTED YET ***]

Notes:

    All parameter values must be bracketed by matching quotes.  Singlequote
    or doublequotes are okay.

    The "startswith" and "regex" filters may be used together.  The "startswith"
    filter is more efficient, since it's passed into the underlyng database query,
    whereas the "regex" filter is applied on the results returned from the database.

Example:

    <<ItemPageList(item="Foo/Bar", ordered='True', display="UnCameled")>>
"""

import re
from flask import request
from flask import g as flaskg
from moin.i18n import _, L_, N_
from moin.utils.tree import moin_page
from moin.utils.interwiki import split_fqname
from moin.macros._base import MacroPageLinkListBase


class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):

        # defaults
        item = None
        startswith = ""
        regex = None
        ordered = False
        display = "FullPath"

        # process input
        args = []
        if arguments:
            args = arguments[0].split(',')
        for arg in args:
            try:
                key, val = [x.strip() for x in arg.split('=')]
            except ValueError:
                raise ValueError(_('Argument "%s" does not follow <key>=<val> format (arguments, if more than one, must be comma-separated).' % arg))

            if len(val) < 2 or (val[0] != "'" and val[0] != '"') and val[-1] != val[0]:
                raise ValueError(_("The key's value must be bracketed by matching quotes."))
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
                    raise ValueError(_('The value must be "True" or "False". (got "%s")' % val))
            elif key == "display":
                display = val  # let 'create_pagelink_list' throw an exception if needed
            else:
                raise KeyError(_('Unrecognized key "%s".' % key))

        # use curr page if not specified
        if item is None:
            item = request.path[1:]

        # test if item doesn't exist (potentially due to user's ACL, but that doesn't matter)
        if item != "": # why are we retaining this behavior from PagenameList?
            if not flaskg.storage.get_item(**(split_fqname(item).query)):
                raise LookupError(_('The specified item "%s" does not exist.' % item))

        # process child pages
        children = self.get_item_names(item, startswith)
        if regex:
            try:
                regex_re = re.compile(regex, re.IGNORECASE)
            except re.error as err:
                raise ValueError(_("Error in regex {0!r}: {1}".format(regex, err)))
            newlist = []
            for child in children:
                if regex_re.search(child):
                    newlist.append(child)
            children = newlist
        if not children:
            empty_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
            item_body = moin_page.list_item_body(children=[_("<No matching pages were found>")])
            item = moin_page.list_item(children=[item_body])
            empty_list.append(item)
            return empty_list
        return self.create_pagelink_list(children, ordered, display)

