# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro base class
"""


from MoinMoin.util import iri
from MoinMoin.util.tree import moin_page, xlink

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

    The macro is wrapped into a paragraph in block context.
    """
    def __call__(self, content, arguments, page_url, alternative, context_block):
        ret = self.macro(content, arguments, page_url, alternative)
        if context_block:
            return moin_page.p(children=(ret, ))
        return ret

class MacroInlineOnlyBase(MacroBase):
    """
    Macro base class for strict inline element macros.

    The macro is only expanded in inline context. In block context it expands
    to nothing.
    """
    def __call__(self, content, arguments, page_url, alternative, context_block):
        if not content_block:
            return self.macro(content, arguments, page_url, alternative)

class MacroPageLinkListBase(MacroBlockBase):
    def create_pagelink_list(self, pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for pagename in pagenames:
            # This link can never reach pagelinks
            url = unicode(iri.Iri(scheme=u'wiki', authority=u'', path=u'/' + pagename))
            pagelink = moin_page.a(attrib={xlink.href: url}, children=[pagename])
            item_body = moin_page.list_item_body(children=[pagelink])
            item = moin_page.list_item(children=[item_body])
            page_list.append(item)
        return page_list

class MacroNumberPageLinkListBase(MacroBlockBase):
    def create_number_pagelink_list(self, num_pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        num_page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for num, pagename in num_pagenames:
            num_code = moin_page.code(children=["%6d " % num])
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

