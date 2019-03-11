# Copyright: 2019 MoinMoin:KentWatsen
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
ItemPageList - return a list of child pages to the specified page.

  Only child pages the user has access to are returned.  If there are no
  child pages to return, then it displays "This page has no children.".

Parameters:

    item: the wiki item to select.  If no item is specified, then the
          current page is used.


    startswith: the substring the item's descendents must begin with.
                If no value is specified, then no name-filtering is applied.

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

    numsep: Only if "display" is UnCameled, what separator string to use
            between a block of letters (upper or lower) preceding a block
            of numbers.  The default is the empty string.  Other likely
            choices are space (' ') and dash ('-').

    Note: All parameter values must be bracketed by matching quotes!
          Singlequote or doublequotes are okay.

Example:

    <<ItemPageList(item="Foo/Bar", ordered='True', display="UnCameled", numsep='')>>
"""

import re
from flask import request
from moin.macros._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self, content, arguments, page_url, alternative):

        # defaults
        item = None
        startswith = ""
        regex = None
        ordered = False
        display = "FullPath"
        numsep = ""

        # process input
        args = []
        if arguments:
          args = arguments[0].split(',')
        for arg in args:
            try:
                key,val = [x.strip() for x in arg.split('=')]
            except ValueError:
                raise ValueError('argument "%s" does not follow <key>=<val> format.' % arg)

            if len(val)<2 or (val[0] != "'" and val[0] != '"') and val[-1] != val[0]:
                raise ValueError('item value must be bracketed by matching quotes.')
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
                    raise ValueError('value "ordered" must be "True" or "False".')
            elif key == "display":
                display = val  # let 'create_pagelink_list' throw an exception if needed
            elif key == "numsep":
                numsep = val
            else:
                raise ValueError('unrecognized key "%s".' % key)

        # use curr page if not specified
        if item is None:
          item = request.path[1:]

        # process child pages
        children=self.get_item_names(item, startswith)
        if regex:
            try:
                regex_re = re.compile(regex, re.IGNORECASE)
            except:
                raise ValueError("Error in regex {0!r}: {1}".format(regex, err))
            newlist = []
            for child in children:
                if regex_re.search(child):
                    newlist.append(child)
            children = newlist
        if not children:
            return "This page has no children."
        return self.create_pagelink_list(children, ordered, display, numsep)
