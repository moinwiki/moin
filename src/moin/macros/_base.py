# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro base class
"""

from werkzeug.exceptions import abort

from moin.utils import iri
from moin.utils.tree import moin_page, xlink
from moin.items import Item
from moin.storage.middleware.protecting import AccessDenied
import re


class MacroBase(object):
    """
    Macro base class.
    """

    # The output of a immutable macro only depends on the arguments and the content
    immutable = False

    def __init__(self):
        pass

    def __call__(self, content, arguments, page_url, alternative, context_block):
        raise NotImplementedError


class MacroBlockBase(MacroBase):
    """
    Macro base class for block element macros.

    The macro gets only expanded in block context. In inline context the
    alternative text is used instead.
    """
    def __call__(self, content, arguments, page_url, alternative, context_block):
        if context_block:
            return self.macro(content, arguments, page_url, alternative)
        return self.alt

    def macro(self, content, arguments, page_url, alternative):
        raise NotImplementedError


class MacroInlineBase(MacroBase):
    """
    Macro base class for inline element macros.

    The macro is wrapped into a div in block context.
    """
    def __call__(self, content, arguments, page_url, alternative, context_block):
        ret = self.macro(content, arguments, page_url, alternative)
        if context_block:
            return moin_page.div(children=(ret, ))
        return ret


class MacroInlineOnlyBase(MacroBase):
    """
    Macro base class for strict inline element macros.

    The macro is only expanded in inline context. In block context it expands
    to nothing.
    """
    def __call__(self, content, arguments, page_url, alternative, context_block):
        if not context_block:
            return self.macro(content, arguments, page_url, alternative)


class MacroPageLinkListBase(MacroBlockBase):
    def create_pagelink_list(self, pagenames, ordered=False, display="FullPath", numsep=""):
        """ Creates an ET with a list of pagelinks from a list of pagenames.

            Parameters:

              pagenames: a list of pages, each being like a flask request.path[1:]

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
                      PageTitle : Use the title from the first header in the linked page

              numsep: if display is UnCameled, what separator string to use
                      between a block of letters (upper or lower) preceding
                      a block of numbers.  Default is the empty string.
            """

        page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for pagename in pagenames:
            # This link can never reach pagelinks
            url = unicode(iri.Iri(scheme=u'wiki', authority=u'', path=u'/' + pagename))

            if display == "FullPath":
                linkname = pagename
            elif display == "ChildPath":
                index = pagename.rfind('/')
                linkname = pagename[index:]
            elif display == "ChildName":
                index = pagename.rfind('/')
                linkname = pagename[index+1:]
            elif display == "UnCameled":
                index = pagename.rfind('/')
                tempname = re.sub("([a-z0-9])([A-Z])", r"\g<1> \g<2>", pagename[index+1:])  # space before a cap char
                linkname = re.sub("([a-zA-Z])([0-9])", r"\g<1>%s\g<2>" % numsep, tempname)
            elif display == "PageTitle":
                raise Exception("PageTitle isn't implemented yet.")
            else:
                raise ValueError('unrecognized display value "%s".' % display)

            pagelink = moin_page.a(attrib={xlink.href: url}, children=[linkname])
            item_body = moin_page.list_item_body(children=[pagelink])
            item = moin_page.list_item(children=[item_body])
            page_list.append(item)
        return page_list

    def get_item_names(self, name='', startswith='', kind='files'):
        """
        For the specified item, return the fullname of natching descndents.

        Input:

           name: the name of the item to get.  If '' is passed, then the
                 top-level item is used.

           startwith: a substring the matching pages must begin with.  If no
                      value is specified, then all pages are returned.

           kind: the kind of page to return.  Valid values include:

                 files: decendents that do not contain decendents. (default)
                 dirs:  decendents that contain decendents.
                 both:  both 'files' and 'dirs', with duplicates removed.

        Output:

           A List of descendent items using their "fullname" value
        """
        try:
            item = Item.create(name)
        except AccessDenied:
            abort(403)
        dirs, files = item.get_index(startswith)
        item_names = []
        if not kind or kind == "files" or kind == "both":
            for item in files:
                item_names.append(item.fullname.value)
        if kind == "dirs" or kind == "both":
            for item in dirs:
                item_names.append(item.fullname.value)
        if kind == "both":
            item_names = list(set(item_names))  # remove duplicates
        return item_names


class MacroNumberPageLinkListBase(MacroBlockBase):
    def create_number_pagelink_list(self, num_pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        num_page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for num, pagename in num_pagenames:
            num_code = moin_page.code(children=["{0:6d} ".format(num)])
            # This link can never reach pagelinks
            url = unicode(iri.Iri(scheme=u'wiki', authority=u'', path=u'/' + pagename))
            pagelink = moin_page.a(attrib={xlink.href: url}, children=[pagename])
            item_body = moin_page.list_item_body(children=[num_code, pagelink])
            item = moin_page.list_item(children=[item_body])
            num_page_list.append(item)
        return num_page_list


class MacroDefinitionListBase(MacroBlockBase):
    def create_definition_list(self, items):
        """ creates an ET with a definition list made from items """
        def_list = moin_page.list()
        for label, body in items:
            item_label = moin_page.list_item_label(children=[label])
            item_body = moin_page.list_item_body(children=[body])
            item = moin_page.list_item(children=[item_label, item_body])
            def_list.append(item)
        return def_list
