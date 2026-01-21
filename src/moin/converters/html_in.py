# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2026 Günter Milde
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - HTML input converter.

Convert an XHTML document into an internal document tree.

TODO: add support for style.
"""

from __future__ import annotations

from typing import Any, Final, TYPE_CHECKING

import re

from flask import flash

from emeraldtree import ElementTree as ET
from emeraldtree.html import HTML

from markupsafe import escape

from moin.i18n import _
from moin.utils.tree import html, moin_page, xlink, xml
from moin.utils.mime import Type, type_moin_document

from . import default_registry
from ._util import decode_data, normalize_split_text, sanitise_uri_scheme

from moin import log

if TYPE_CHECKING:
    from moin.converters._args import Arguments
    from typing_extensions import Self

logging = log.getLogger(__name__)


class NoDupsFlash:
    """
    Issue flash messages for unsupported HTML tags; but do not create duplicate messages.
    """

    def __init__(self):
        self.messages = set()

    def log(self, message, category):
        if message not in self.messages:
            self.messages.add(message)
            try:
                flash(message, category)
            except RuntimeError:  # CLI call has no valid request context
                pass


class HtmlTags:
    """
    Common definitions for HTML and Markdown converters.
    """

    # Namespace of our input data
    html_namespace: Final = {html.namespace: "xhtml"}

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags: Final = {"blockquote", "code", "del", "div", "ins", "p", "s", "span", "strong", "u"}

    # HTML tags that define a list; except dl, which is a little bit different
    list_tags: Final = {"ul", "dir", "ol"}

    # HTML tags with a matching but differently named Moinpage DOM tag
    simple_tags: Final = {
        # Inline text markup (text level semantics)
        "em": moin_page.emphasis,
        "b": moin_page.strong,  # highlight key words without marking them up as important
        "q": moin_page.quote,
        "strike": moin_page.s,  # obsolete
        # Code and Blockcode
        "pre": moin_page.blockcode,
        "tt": moin_page.code,  # deprecated
        "samp": moin_page.code,  # computer output sample
        # Lists
        "dt": moin_page.list_item_label,
        "dd": moin_page.list_item_body,
        # Tables -- table, th, and td require special processing
        "thead": moin_page.table_header,
        "tfoot": moin_page.table_footer,
        "tbody": moin_page.table_body,
        "tr": moin_page.table_row,
    }

    # HTML tags that do not have equivalents in the Moinpage DOM tree
    # we use a more generic element and store the original tag as class value
    # e.g. <cite> → <emphasis class="html-cite}">
    indirect_tags: Final = {
        # emphasized text (default style: italic)
        "cite": moin_page.emphasis,  # title of a creative work
        "dfn": moin_page.emphasis,  # defining instance of a term
        "i": moin_page.emphasis,  # alternate voice
        "var": moin_page.emphasis,  # variable
        # misc (no common default style)
        "abbr": moin_page.span,
        "mark": moin_page.span,
        "small": moin_page.span,  # side comment (small print)
        "kbd": moin_page.span,  # user input;  TODO: use moin_page.code?
    }

    # HTML tags that are completely ignored by our converter.
    # Deprecated/obsolete tags and tags not suited for wiki content
    # We do not even process children of these elements, a warning is given.
    ignored_tags: Final = {
        "applet",
        "area",
        "button",
        "caption",
        "center",
        "fieldset",
        "form",
        "frame",
        "frameset",
        "head",
        "iframe",
        "input",
        "isindex",
        "label",
        "legend",
        "link",
        "map",
        "menu",
        "noframes",
        "noscript",
        "optgroup",
        "option",
        "param",
        "script",
        "select",
        "style",
        "textarea",
        "title",
    }

    # standard_attributes are html attributes which are used
    # directly in the DOM tree, without any conversion
    standard_attributes: Final = {"title", "class", "style", "alt"}

    # Regular expression to detect a html heading tag
    heading_re = re.compile("h[1-6]")

    # Store the Base URL for all the URL of the document
    base_url = ""

    def new(self, tag, attrib, children):
        """
        Return a new element for the DOM Tree
        """
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib):
        """
        Function to copy one element to the DOM Tree.

        It first converts the child of the element,
        and the element itself.
        """
        attrib_new = self.convert_attributes(element)
        attrib.update(attrib_new)
        children = self.do_children(element)
        return self.new(tag, attrib, children)


class Converter(HtmlTags):
    """
    Convert HTML -> .x.moin.document.
    """

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs: Any) -> Self:
        return cls()

    def __call__(self, data: Any, contenttype: str | None = None, arguments: Arguments | None = None) -> Any:
        """
        Function called by the converter to process the
        conversion.

        TODO: Add support for different arguments
        """
        self.no_dups_flash = NoDupsFlash()

        text = decode_data(data, contenttype)
        # data cleanup is not needed by html_out, but is needed by moinwiki_out; CKEditor adds unwanted \n\t
        while "\t\t" in text:
            text = text.replace("\t\t", "\t")
        text = text.replace("\r\n\t", "").replace("\n\t", "")

        content = normalize_split_text(text)
        # Be sure we have empty string in the base url
        self.base_url = ""

        # We create an element tree from the HTML content
        # The content is a list of string, line per line
        # We can concatenate all in one string
        html_str = "\n".join(content)
        try:
            html_tree = HTML(html_str)
        except AssertionError as reason:
            # we suspect user has created or uploaded malformed HTML, try to show input as preformatted code
            msg = _("Error: malformed HTML: {reason}.").format(reason=reason)
            msg = f'<div class="error"><p><strong>{msg}</strong></p></div>'
            html_str = "".join(["<html>", msg, "<pre>", escape(html_str), "</pre></html>"])
            try:
                html_tree = HTML(html_str)
            except ValueError:
                msg = _("Error: malformed HTML. Try viewing source with Markup or Modify links.")
                msg = f'<div class="error"><p><strong>{msg}</strong></p></div>'
                html_str = "".join(["<html>", msg, "</html>"])
                html_tree = HTML(html_str)

        # We should have a root element, which will be converted as <page>
        # for the DOM Tree.
        # NB : If <html> used, it will be converted back to <div> after
        # one roundtrip
        if html_tree.tag.name != "html":
            html_str = "".join(["<div>", html_str, "</div>"])
            html_tree = HTML(html_str)

        # Start the conversion of the first element
        # Every child of each element will be recursively convert too
        element = self.do_children(html_tree)

        # Add Global element to our DOM Tree
        body = moin_page.body(children=element)
        root = moin_page.page(children=[body])
        return root

    def do_children(self, element):
        """
        Function to process the conversion of the child of
        a given elements.
        """
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                new.extend(r)
            else:
                new.append(child)
        return new

    def new_copy_symmetric(self, element, attrib):
        """
        Create a new QName, with the same tag of the element,
        but with a different namespace.

        Then, we handle the copy normally.
        """
        tag = ET.QName(element.tag.name, moin_page)
        return self.new_copy(tag, element, attrib)

    def new_copy_indirect(self, element):
        """
        Return a "close match" base-element with the original tag as class value.
        """
        tagname = element.tag.name
        element_type = self.indirect_tags[tagname]
        attrib = {html("class"): f"html-{tagname}"}
        return self.new_copy(element_type, element, attrib)

    def convert_attributes(self, element):
        result = {}
        for key, value in element.attrib.items():
            if key.uri == html and key.name in self.standard_attributes:
                result[key] = value
            if key.name == "id":
                result[xml("id")] = value
        return result

    def visit(self, element):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the found namespace.
        """
        uri = element.tag.uri
        name = self.html_namespace.get(uri, None)
        if name is not None:
            method_name = "visit_" + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)

            # We process children of the unknown element
            return self.do_children(element)

    def visit_xhtml(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the XHTML namespace.

        We will detect the name of the tag, and apply an appropriate
        procedure to convert it.
        """
        # Our element can be converted directly, just by changing the namespace
        if element.tag.name in self.symmetric_tags:
            return self.new_copy_symmetric(element, attrib={})

        # Our element is simple enough to just change the tag name
        if element.tag.name in self.simple_tags:
            return self.new_copy(self.simple_tags[element.tag.name], element, attrib={})

        # We convert our element to a "close match" with class attribute
        if element.tag.name in self.indirect_tags:
            return self.new_copy_indirect(element)

        # Our element defines a list
        if element.tag.name in self.list_tags:
            return self.visit_xhtml_list(element)

        # We have a heading tag
        if self.heading_re.match(element.tag.name):
            return self.visit_xhtml_heading(element)

        # Otherwise we need a specific procedure to handle it
        method_name = "visit_xhtml_" + element.tag.name
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # We should ignore this tag and its content
        if element.tag.name in self.ignored_tags:
            # tell user output from obsolete tags like "center" is suppressed
            msg = _("Tag '{invalid_tag}' is not supported; all tag contents are discarded.").format(
                invalid_tag=element.tag.name
            )
            self.no_dups_flash.log(msg, "info")
            logging.debug(f"WARNING : Ignored tag : {element.tag.name}")
            return

        # Otherwise we process children of the unknown element
        msg = _("Tag '{invalid_tag}' is not known; tag ignored but children are processed.").format(
            invalid_tag=element.tag.name
        )
        self.no_dups_flash.log(msg, "info")
        logging.debug(f"WARNING : Unknown tag : {element.tag.name}")
        return self.do_children(element)

    # TODO: if this is useful, it should be documented. Normally <BASE..> tags are in <HEAD> and
    # browser modifies relative urls.
    # Here the base_url is used to create fully qualified links within A, OBJECT and IMG tags.
    def visit_xhtml_base(self, element):
        """
        Function to store the base url for the relative url of the document
        """
        self.base_url = element.get(html.href)

    def visit_xhtml_heading(self, element):
        """
        Function to convert an heading tag into the proper
        element in our moin_page namespace
        """
        heading_level = element.tag.name[1]
        key = moin_page("outline-level")
        attrib = {}
        attrib[key] = heading_level
        ret = self.new_copy(moin_page.h, element, attrib)
        return ret

    def visit_xhtml_acronym(self, element):
        # in HTML5, <acronym> is deprecated in favour of <abbr>
        attrib = {html.class_: "html-abbr"}
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_address(self, element):
        attrib = {html.class_: "html-address"}
        return self.new_copy(moin_page.div, element, attrib)

    def visit_xhtml_br(self, element):
        """
        <br /> --> <line-break />
        """
        return moin_page.line_break()

    def visit_xhtml_big(self, element):
        """
        <big>Text</big> --> <span font-size=120%>Text</span>
        """
        key = moin_page("font-size")
        attrib = {}
        attrib[key] = "120%"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sub(self, element):
        """
        <sub>Text</sub> --> <span base-line-shift="sub">Text</span>
        """
        key = moin_page("baseline-shift")
        attrib = {}
        attrib[key] = "sub"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sup(self, element):
        """
        <sup>Text</sup> --> <span base-line-shift="super">Text</span>
        """
        key = moin_page("baseline-shift")
        attrib = {}
        attrib[key] = "super"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_hr(self, element, min_class="moin-hr1", max_class="moin-hr6", default_class="moin-hr3"):
        """
        <hr /> --> <separator />
        """
        hr_class = element.attrib.get(html("class"))
        if hr_class is None or not (min_class <= hr_class <= max_class):
            element.attrib[html("class")] = default_class
        return self.new_copy(moin_page.separator, element, {})

    def visit_xhtml_a(self, element):
        """
        <a href="URI">Text</a> --> <a xlink:href="URI">Text</a>
        """
        attrib = {}
        if element.attrib.get("title"):
            attrib[html.title_] = element.attrib.get("title")
        href = element.get(html.href)
        if self.base_url:
            href = "".join([self.base_url, href])
        # ensure a safe scheme, fall back to wiki-internal reference:
        attrib[xlink.href] = sanitise_uri_scheme(href)
        return self.new_copy(moin_page.a, element, attrib)

    def visit_xhtml_img(self, element):
        """
        <img src="URI" /> --> <object xlink:href="URI />
        """
        key = xlink.href
        attrib = self.convert_attributes(element)
        # adding type_ attrib makes html_out create an image tag rather than an object tag
        attrib[moin_page.type_] = "image/"
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.src)])
        else:
            attrib[key] = element.get(html.src)
        return moin_page.object(attrib)

    def visit_xhtml_object(self, element):
        """
        <object data="href"></object> --> <object xlink="href" />
        """
        key = xlink.href
        attrib = {}
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.data)])
        else:
            attrib[key] = element.get(html.data)

        # Convert the href attribute into unicode
        attrib[key] = str(attrib[key])
        return moin_page.object(attrib)

    def visit_xhtml_audio(self, element):
        """
        <audio src="URI" /> --> <audio xlink:href="URI />
        """
        attrib = {}
        key = xlink.href
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.src)])
        else:
            attrib[key] = element.get(html.src)
        for key, value in element.attrib.items():
            if key.uri == html and key.name in ("controls",):
                attrib[key] = value
            if key.name == "id":
                attrib[xml("id")] = value
        return moin_page.audio(attrib)

    def visit_xhtml_video(self, element):
        """
        <video src="URI" /> --> <video xlink:href="URI />
        """
        attrib = {}
        key = xlink.href
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.src)])
        else:
            attrib[key] = element.get(html.src)
        for key, value in element.attrib.items():
            if key.uri == html and key.name in ("controls", "width", "height", "autoplay"):
                attrib[key] = value
            if key.name == "id":
                attrib[xml("id")] = value
        return moin_page.video(attrib)

    def visit_xhtml_list(self, element):
        """
        Convert a list of items (whatever the type : ordered or unordered)
        So we have html code like::

            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>

        Which will be converted to::

            <list>
                <list-item>
                    <list-item-body>Item 1</list-item-body>
                </list-item>
                <list-item>
                    <list-item-body>Item 2</list-item-body>
                </list-item>
            </list>
        """
        # We will define the appropriate attribute
        # according to the type of the list
        attrib = self.convert_attributes(element)
        if element.tag.name == "ul" or element.tag.name == "dir":
            attrib[moin_page("item-label-generate")] = "unordered"
        elif element.tag.name == "ol":
            attrib[moin_page("item-label-generate")] = "ordered"

            # We check which kind of style we have
            style = element.get(html.type)
            if "A" == style:
                attrib[moin_page("list-style-type")] = "upper-alpha"
            elif "I" == style:
                attrib[moin_page("list-style-type")] = "upper-roman"
            elif "a" == style:
                attrib[moin_page("list-style-type")] = "lower-alpha"
            elif "i" == style:
                attrib[moin_page("list-style-type")] = "lower-roman"

        # we should not have any strings in the child
        list_items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                list_items.extend(r)
        return ET.Element(moin_page.list, attrib=attrib, children=list_items)

    def visit_xhtml_dl(self, element):
        """
        Convert a list of definition. The starting structure::

            <dl>
                <dt>Label 1</dt><dd>Text 1</dd>
                <dt>Label 2</dt><dd>Text 2</dd>
            </dl>

        will be converted to::

            <list>
                <list-item>
                    <list-item-label>Label 1</list-item-label>
                    <list-item-body>Text 1</list-item-body>
                </list-item>
                <list-item>
                    <list-item-label>Label 2</list-item-label>
                    <list-item-body>Text 2</list-item-body>
                </list-item>
            </list>
        """
        list_item = []
        pair = []
        number_pair = 0
        # We will browse the child, and try to catch all the pair
        # of <dt><dd>
        for child in element:
            # We need one dt tag, and one dd tag, a have a pair
            if child.tag.name == "dt" or child.tag.name == "dd":
                number_pair += 1

            # The following code is similar to do_children method
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                pair.extend(r)
            else:
                pair.append(r)

            if number_pair == 2:
                # We have two elements of the pair
                # So we can put it into a <list-item> element
                list_item_element = ET.Element(moin_page.list_item, attrib={}, children=pair)
                list_item.append(list_item_element)
                pair = []
                number_pair = 0

        # we return the <list> with all the list item element
        return ET.Element(moin_page.list, attrib={}, children=list_item)

    def visit_xhtml_li(self, element):
        """
        NB : A list item (<li>) is like the following snippet::

            <list-item>
                <list-item-label>label</list-item-label>
                <list-item-body>Body</list-item-body>
            </list-item>

        For <li> element, there is no label
        """
        list_item_body = ET.Element(moin_page.list_item_body, attrib={}, children=self.do_children(element))
        return ET.Element(moin_page.list_item, attrib={}, children=[list_item_body])

    def visit_xhtml_table(self, element):
        attrib = self.convert_attributes(element)
        # we should not have any strings in the child
        list_table_elements = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                list_table_elements.extend(r)
        return ET.Element(moin_page.table, attrib=attrib, children=list_table_elements)

    # TODO: caption is currently in `ignored_tags`!
    def visit_xhtml_caption(self, element):
        return self.new_copy(moin_page.caption, element, attrib={})

    def visit_xhtml_td(self, element):
        attrib = self.rowspan_colspan(element)
        return self.new_copy(moin_page.table_cell, element, attrib=attrib)

    def visit_xhtml_th(self, element):
        attrib = self.rowspan_colspan(element)
        return self.new_copy(moin_page.table_cell_head, element, attrib=attrib)

    def rowspan_colspan(self, element):
        attrib = {}
        rowspan = element.get(html.rowspan)
        colspan = element.get(html.colspan)
        if rowspan:
            attrib[moin_page("number-rows-spanned")] = rowspan
        if colspan:
            attrib[moin_page("number-columns-spanned")] = colspan
        return attrib


default_registry.register(Converter._factory, Type("text/html"), type_moin_document)
