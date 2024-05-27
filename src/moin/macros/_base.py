# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro base class
"""

import re

from moin.constants.keys import CURRENT, CONTENTTYPE
from moin.utils import iri
from moin.items import Item
from moin.utils.tree import html
from moin.i18n import _
from werkzeug.exceptions import abort
from moin.utils.tree import moin_page, xlink
from moin.storage.middleware.protecting import AccessDenied
from moin.constants.keys import TAGS


def get_item_names(name="", startswith="", kind="files", skiptag=""):
    """
    For the specified item, return the fullname of matching descendents.

    Input:

       name: the name of the item to get.  If '' is passed, then the
             top-level item is used.

       startwith: a substring the matching pages must begin with.  If no
                  value is specified, then all pages are returned.

       kind: the kind of page to return.  Valid values include:

             files: decendents that do not contain decendents. (default)
             dirs:  decendents that contain decendents.
             both:  both 'files' and 'dirs', with duplicates removed.

        skiptag: skip items having this tag

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
            if skiptag and TAGS in item.meta and skiptag in item.meta[TAGS]:
                continue
            item_names.append(item.fullname)
    if kind == "dirs" or kind == "both":
        for item in dirs:
            if skiptag and skiptag in item.meta[TAGS]:
                continue
            item_names.append(item.fullname)
    if kind == "both":
        item_names = list(set(item_names))  # remove duplicates
    return item_names


def extract_h1(item_name):
    """
    Return the first heading found in the item's content
    """
    item = Item.create(item_name, rev_id=CURRENT)
    contenttype = item.meta[CONTENTTYPE]
    if "x.moin.wiki" not in contenttype and "x.moin.creole" not in contenttype:
        return _("{item_name} content type is not moinwiki or creole").format(item_name=item_name)
    item.rev.data.seek(0)
    content = item.rev.data.read()
    content = content.decode("utf-8")
    lines = content.splitlines()
    for line in lines:
        line = line.rstrip()
        if line:
            if line.startswith("=") and line.endswith("="):
                title = line.replace("=", "").strip()
                return title
    return _("No heading found in item: {item_name}").format(item_name=item_name)


def fail_message(msg, alternative, severity="error"):
    """
    Return an error message in admonition-like format.

    :param msg: error message
    :param alternative: full text of macro as passed in MacroBase __call__
    :param Severity: attention, caution, danger, error, hint, important, note, or tip
    :returns: formatted text of macro, error message
    """
    if severity not in "attention caution danger error hint important note tip".split():
        raise ValueError

    altern = html.p(children=[html.strong(children=[alternative])])
    message = html.p(children=[msg])
    return html.div(attrib={html.class_: f"{severity} moin-nowiki"}, children=[altern, message])


class MacroBase:
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

    The macro gets only expanded in block context.
    """

    def __call__(self, content, arguments, page_url, alternative, context_block):
        if context_block:
            return self.macro(content, arguments, page_url, alternative)
        err_msg = _("Block macros cannot be used inline")
        return fail_message(err_msg, alternative)

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
            return moin_page.div(children=(ret,))
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
    def create_pagelink_list(self, pagenames, alternative, ordered=False, display="FullPath"):
        """Creates an ET with a list of pagelinks from a list of pagenames.

        Parameters:

          pagenames: a list of pages, each being like a flask request.path[1:]

          alternative: full text of macro call

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
                  skiptag   : skip items with this tag
                  ItemTitle : Use the title from the first header in the linked page
        """

        page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and "ordered" or "unordered"})

        for pagename in pagenames:

            fqname = pagename.fullname
            # This link can never reach pagelinks
            url = str(iri.Iri(scheme="wiki", authority="", path="/" + fqname))

            if display == "FullPath":
                linkname = pagename
            elif display == "ChildPath":
                index = fqname.rfind("/")
                if index == -1:
                    linkname = fqname
                else:
                    linkname = fqname[index:]
            elif display == "ChildName":
                index = fqname.rfind("/")
                linkname = fqname[(index + 1) :]
            elif display == "UnCameled":
                index = fqname.rfind("/")
                tempname = re.sub("([a-z0-9])([A-Z])", r"\g<1> \g<2>", fqname[(index + 1) :])  # space before a cap char
                linkname = re.sub("([a-zA-Z])([0-9])", r"\g<1> \g<2>", tempname)
            elif display == "ItemTitle":
                linkname = extract_h1(pagename.fullname)
            else:
                err_msg = _('Unrecognized display value "{display}".').format(display=display)
                return fail_message(err_msg, alternative)

            pagelink = moin_page.a(attrib={xlink.href: url}, children=[linkname])
            item_body = moin_page.list_item_body(children=[pagelink])
            item = moin_page.list_item(children=[item_body])
            page_list.append(item)

        return page_list


class MacroMultiLinkListBase(MacroBlockBase):
    def create_multi_pagelink_list(self, itemnames, namespace):
        """Creates an ET with a list of itemlinks from a list of itemnames
        grouped by initials.

        Parameters:

          itemnames: a list of items, each being like a flask request.path[1:]

          namespace: Namespace of items
        """
        result_body = []
        initials_linklist = []
        initial_letter = " "

        if namespace == "":
            namespace_name = _("Namespace '{name}' ").format(name="default")
            pos_namespace_cut = 0
        else:
            namespace_name = _("Namespace '{name}' ").format(name=namespace)
            pos_namespace_cut = len(namespace) + 1

        item_list = moin_page.list(attrib={moin_page.item_label_generate: "unordered"})
        initials_link = moin_page.a(attrib={xlink.href: "#idx-top"}, children=["top"])
        initials_linklist.extend([initials_link, moin_page.strong(children=[" | "])])

        for itemname in itemnames:
            if not itemname.value.startswith(initial_letter):
                # generate header line with initial
                initial_letter = itemname.value[0]
                result_body.append(item_list)  # finish item_list for last initial and initialize new item_list
                item_list = moin_page.list(attrib={moin_page.item_label_generate: "unordered"})

                header_with_anchor = moin_page.span(
                    attrib={moin_page.class_: "moin-big", moin_page.id: "idx-" + initial_letter},
                    children=[
                        initial_letter,
                        moin_page.a(
                            attrib={moin_page.class_: "moin-align-right", xlink.href: "#idx-top"}, children=["^"]
                        ),
                    ],
                )
                result_body.append(header_with_anchor)
                initials_link = moin_page.a(attrib={xlink.href: "#idx-" + initial_letter}, children=[initial_letter])
                initials_linklist.extend([initials_link, moin_page.strong(children=[" | "])])

            # build and add itemname link
            fqname = itemname.fullname
            url = str(iri.Iri(scheme="wiki", authority="", path="/" + fqname))
            linkname = fqname[pos_namespace_cut:]
            pagelink = moin_page.a(attrib={xlink.href: url}, children=[linkname])
            item_body = moin_page.list_item_body(children=[pagelink])
            item = moin_page.list_item(children=[item_body])
            item_list.append(item)

        result_body.append(item_list)  # finish item_list for last initial

        # Add a list of links for each used initial at top and bottom of the index
        initials_begin = moin_page.span(
            attrib={moin_page.id: "idx-top", moin_page.class_: "moin-align-left"},
            children=[_("Index of {what}").format(what=namespace_name)],
        )
        initials_link_end = moin_page.a(attrib={xlink.href: "#idx-bottom"}, children=["bottom"])
        initials_linklist.append(initials_link_end)
        initials_links_span = moin_page.span(attrib={moin_page.class_: "moin-align-right"}, children=initials_linklist)
        result_body.insert(0, moin_page.p(children=[initials_begin, initials_links_span]))
        initials_end = moin_page.span(
            attrib={moin_page.id: "idx-bottom", moin_page.class_: "moin-align-left"}, children="."
        )
        result_body.append(moin_page.p(children=[initials_end, initials_links_span]))
        return moin_page.body(children=result_body)


class MacroNumberPageLinkListBase(MacroBlockBase):
    def create_number_pagelink_list(self, num_pagenames, ordered=False):
        """creates an ET with a list of pagelinks from a list of pagenames"""
        num_page_list = moin_page.list(attrib={moin_page.item_label_generate: ordered and "ordered" or "unordered"})
        for num, pagename in num_pagenames:
            num_code = moin_page.code(children=[f"{num:6d} "])
            # This link can never reach pagelinks
            url = str(iri.Iri(scheme="wiki", authority="", path="/" + pagename))
            pagelink = moin_page.a(attrib={xlink.href: url}, children=[pagename])
            item_body = moin_page.list_item_body(children=[num_code, pagelink])
            item = moin_page.list_item(children=[item_body])
            num_page_list.append(item)
        return num_page_list


class MacroDefinitionListBase(MacroBlockBase):
    def create_definition_list(self, items):
        """creates an ET with a definition list made from items"""
        def_list = moin_page.list()
        for label, body in items:
            item_label = moin_page.list_item_label(children=[label])
            item_body = moin_page.list_item_body(children=[body])
            item = moin_page.list_item(children=[item_label, item_body])
            def_list.append(item)
        return def_list
