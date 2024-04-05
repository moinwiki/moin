# Copyright: 2008-2010 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Markdown input converter

https://daringfireball.net/projects/markdown/
"""

import re
from html.entities import name2codepoint
from collections import deque

from moin.utils.tree import moin_page, xml, html, xlink, xinclude
from ._util import decode_data
from moin.utils.iri import Iri
from moin.converters.html_in import Converter as HTML_IN_Converter

from emeraldtree import ElementTree as ET

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from markdown import Markdown
import markdown.util as md_util
from markdown.extensions.extra import ExtraExtension
from markdown.extensions.codehilite import CodeHiliteExtension

from . import default_registry
from moin.utils.mime import Type, type_moin_document

from moin import log

logging = log.getLogger(__name__)

html_in_converter = HTML_IN_Converter()
block_elements = "p h blockcode ol ul pre address blockquote dl div fieldset form hr noscript table".split()
BLOCK_ELEMENTS = {moin_page(x) for x in block_elements}


def postproc_text(markdown, text):
    """
    Removes HTML or XML character references and entities from a text string.

    :param text: The HTML (or XML) source text.
    :returns: The plain text, as a Unicode string, if necessary.
    """

    # http://effbot.org/zone/re-sub.htm#unescape-html

    if text is None:
        return None

    if text == "[TOC]":
        return moin_page.table_of_content(attrib={})

    for pp in markdown.postprocessors:
        text = pp.run(text)

    if text.startswith("<pre>") or text.startswith('<div class="codehilite"><pre>'):
        return text

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub(r"&#?\w+;", fixup, text)


class Converter:
    # {{{ html conversion

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags = {"div", "p", "strong", "code", "quote", "blockquote"}

    # HTML tags to define a list, except dl which is a little bit different
    list_tags = {"ul", "ol"}

    # HTML tags which can be convert without attributes in a different DOM tag
    simple_tags = {  # Emphasis
        "em": moin_page.emphasis,
        "i": moin_page.emphasis,
        # Strong
        "b": moin_page.strong,
        "strong": moin_page.strong,
        # Code and Blockcode
        "pre": moin_page.blockcode,
        "tt": moin_page.code,
        "samp": moin_page.code,
        # Lists
        "dl": moin_page.list_item,
        "dt": moin_page.list_item_label,
        "dd": moin_page.list_item_body,
        # Table - th and td require special processing for alignment of cell contents
        "table": moin_page.table,
        "thead": moin_page.table_header,
        "tbody": moin_page.table_body,
        "tr": moin_page.table_row,
    }

    # HTML Tag which does not have equivalence in the DOM Tree
    # But we keep the information using <span element>
    inline_tags = {"abbr", "acronym", "address", "dfn", "kbd"}

    # HTML tags which are completely ignored by our converter.
    # We even do not process children of these elements.
    ignored_tags = {
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
        "var",
    }

    # standard_attributes are html attributes which are used
    # directly in the DOM tree, without any conversion
    standard_attributes = {"title", "class", "style"}

    # Regular expression to detect an html heading tag
    heading_re = re.compile("h[1-6]")

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

    def new_copy_symmetric(self, element, attrib):
        """
        Create a new QName, with the same tag of the element,
        but with a different namespace.

        Then, we handle the copy normally.
        """
        tag = ET.QName(element.tag, moin_page)
        return self.new_copy(tag, element, attrib)

    def convert_attributes(self, element):
        result = {}
        for key, value in element.attrib.items():
            if key in self.standard_attributes:
                result[moin_page(key)] = value
            if key == "id":
                result[xml("id")] = value
        return result

    def visit_heading(self, element):
        """
        Function to convert an heading tag into a proper
        element in our moin_page namespace
        """
        heading_level = element.tag[1]
        key = moin_page("outline-level")
        attrib = {}
        attrib[key] = heading_level
        return self.new_copy(moin_page.h, element, attrib)

    def visit_br(self, element):
        return moin_page.line_break()

    def visit_big(self, element):
        key = moin_page("font-size")
        attrib = {}
        attrib[key] = "120%"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_small(self, element):
        key = moin_page("font-size")
        attrib = {}
        attrib[key] = "85%"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_sub(self, element):
        key = moin_page("baseline-shift")
        attrib = {}
        attrib[key] = "sub"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_sup(self, element):
        key = moin_page("baseline-shift")
        attrib = {}
        attrib[key] = "super"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_u(self, element):
        key = moin_page("text-decoration")
        attrib = {}
        attrib[key] = "underline"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_ins(self, element):
        key = moin_page("text-decoration")
        attrib = {}
        attrib[key] = "underline"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_del(self, element):
        key = moin_page("text-decoration")
        attrib = {}
        attrib[key] = "line-through"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_s(self, element):
        key = moin_page("text-decoration")
        attrib = {}
        attrib[key] = "line-through"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_strike(self, element):
        key = moin_page("text-decoration")
        attrib = {}
        attrib[key] = "line-through"
        return self.new_copy(moin_page.span, element, attrib)

    def visit_hr(self, element, default_class="moin-hr3"):
        return self.new_copy(moin_page.separator, element, {moin_page.class_: default_class})

    def visit_img(self, element):
        """
        <img src="URI" /> --> <object xlink:href="URI />
        """
        attrib = {}
        url = Iri(element.attrib.get("src"))
        if element.attrib.get("alt"):
            attrib[html.alt] = element.attrib.get("alt")
        if element.attrib.get("title"):
            attrib[html.title_] = element.attrib.get("title")
        if url.scheme is None:
            # img tag
            target = Iri(scheme="wiki.local", path=element.attrib.get("src"), fragment=None)
            attrib[xinclude.href] = target
            new_node = xinclude.include(attrib=attrib)
        else:
            # object tag
            attrib[xlink.href] = url
            new_node = moin_page.object(attrib)
        return new_node

    def visit_object(self, element):
        """
        <object data="href"></object> --> <object xlink="href" />
        """
        key = xlink("href")
        attrib = {}
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.data)])
        else:
            attrib[key] = element.get(html.data)

        # Convert the href attribute into unicode
        attrib[key] = str(attrib[key])
        return moin_page.object(attrib)

    def visit_inline(self, element):
        """
        For some specific inline tags (defined in inline_tags)
        We just return <span element="tag.name">
        """
        key = html.class_
        attrib = {}
        attrib[key] = "".join(["html-", element.tag.name])
        return self.new_copy(moin_page.span, element, attrib)

    def visit_li(self, element):
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

    def visit_list(self, element):
        """
        Convert a list of item (whatever the type : ordered or unordered)
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
        attrib = {}
        if element.tag == "ul" or element.tag == "dir":
            attrib[moin_page("item-label-generate")] = "unordered"
        elif element.tag == "ol":
            attrib[moin_page("item-label-generate")] = "ordered"

        return ET.Element(moin_page.list, attrib=attrib, children=self.do_children(element))

    def visit_a(self, element):
        """element.attrib has href, element.tag is 'a', element.text has title"""
        key = xlink("href")
        attrib = {}
        if element.attrib.get("title"):
            attrib[html.title_] = element.attrib.get("title")
        href = postproc_text(self.markdown, element.attrib.get("href"))
        iri = Iri(href)
        # iri has authority, fragment, path, query, scheme = none,none,path,none
        if iri.scheme is None:
            iri.scheme = "wiki.local"
        attrib[key] = iri
        return self.new_copy(moin_page.a, element, attrib)

    def verify_align_style(self, attrib):
        alignment = attrib.get("style")
        if alignment and alignment in ("text-align: right;", "text-align: center;", "text-align: left;"):
            attrib = {moin_page.style: attrib.get("style")}
            return attrib
        return {}

    def visit_th(self, element):
        attrib = self.verify_align_style(element.attrib)
        return self.new_copy(moin_page.table_cell_head, element, attrib=attrib)

    def visit_td(self, element):
        attrib = self.verify_align_style(element.attrib)
        return self.new_copy(moin_page.table_cell, element, attrib=attrib)

    def visit(self, element):
        # Our element can be converted directly, just by changing the namespace
        if element.tag in self.symmetric_tags:
            return self.new_copy_symmetric(element, attrib={})

        # Our element is enough simple to just change the tag name
        if element.tag in self.simple_tags:
            return self.new_copy(self.simple_tags[element.tag], element, attrib={})

        # Our element defines a list
        if element.tag in self.list_tags:
            return self.visit_list(element)

        # We convert our element as a span tag with element attribute
        if element.tag in self.inline_tags:
            return self.visit_inline(element)

        # We have a heading tag
        if self.heading_re.match(element.tag):
            return self.visit_heading(element)

        # Otherwise we need a specific procedure to handle it
        method_name = "visit_" + element.tag
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # We should ignore this tag
        if element.tag in self.ignored_tags:
            logging.info(f"INFO : Ignored tag : {element.tag}")
            return

        logging.info(f"INFO : Unhandled tag : {element.tag}")
        return

    # }}} end of html conversion

    def do_children(self, element, add_lineno=False):
        """
        Incoming element is an ElementTree object or unicode,
        an EmeraldTree object or a list of unicode is returned.

        Markdown parser may have set text and tail attributes of ElementTree
        objects to "\n" values, omit these.

        Add data-lineno attributes to children if requested.
        """
        new = []
        # copy anything but '\n'
        if hasattr(element, "text") and element.text is not None and element.text != "\n":
            new.append(postproc_text(self.markdown, element.text))

        for child in element:
            r = self.visit(child)
            if r is None:
                r = ()
            elif not isinstance(r, (list, tuple)):
                if add_lineno and self.line_numbers:
                    # the line numbers for the start of each block were counted and saved before preprocessors were run
                    r.attrib[html.data_lineno] = self.line_numbers.popleft()
                r = (r,)
            new.extend(r)
            # copy anything but '\n'
            if hasattr(child, "tail") and child.tail is not None and child.tail != "\n" and child.tail:
                new.append(postproc_text(self.markdown, child.tail))
        return new

    def count_lines(self, text):
        """
        Create a list of line numbers corresponding to the first line of each markdown block.

        The markdown parser does not provide text line numbers nor is there an easy way to
        add line numbers. As an alternative, we try to split the input text into the same blocks
        as the parser does, then calculate the starting line number of each block.  The list will be
        processed by the do_children method above.

        This method has unresolved problems caused by splitting the text into blocks based upon
        the presence of 2 adjacent line end characters, including:

            * blank lines within lists create separate blocks
            * omitting a blank line after a heading combines 2 elements into one block
            * using more than one blank lines between blocks

        The net result is we either have too few or too many line numbers in the generated list which
        will cause the double-click-to-edit autoscroll textarea to sometimes be off by several lines.
        """
        line_numbers = deque()
        lineno = 1
        in_blockquote = False
        blocks = text.split("\n\n")
        for block in blocks:
            if not block:
                # bump count because empty blocks will be discarded
                lineno += 2
                continue
            line_count = block.count("\n")

            # detect and fix the problem of interspersed blank lines within blockquotes
            if block.startswith("    ") or block.startswith("\n    "):
                if in_blockquote:
                    lineno += line_count + 2
                    continue
                in_blockquote = True
            else:
                in_blockquote = False

            if block.startswith("\n"):
                lineno += 1
                line_numbers.append(lineno)
                lineno += line_count + 2 - 1  # -1 is already in count
            else:
                line_numbers.append(lineno)
                lineno += line_count + 2
        self.line_numbers = line_numbers

    def embedded_markup(self, text):
        """
        Allow embedded raw HTML markup per https://daringfireball.net/projects/markdown/syntax#html
        This replaces the functionality of RawHtmlPostprocessor in .../markdown/postprocessors.py.

        To prevent hackers from exploiting raw HTML, the strings of safe HTML are converted to
        tree nodes by using the html_in.py converter.
        """
        try:
            # we enclose plain text and span tags with P-tags
            p_text = html_in_converter(f"<p>{text}</p>")
            # discard page and body tags
            return p_text[0][0]
        except AssertionError:
            # malformed tags, will be escaped so user can see and fix
            return text

    def convert_embedded_markup(self, node):
        """
        Recurse through tree looking for embedded or generated markup.

        :param node: a tree node
        """
        for idx, child in enumerate(node):
            if isinstance(child, str):
                if "<" in child:
                    node[idx] = self.embedded_markup(child)  # child is immutable string, so must do node[idx]
            else:
                # do not convert markup within a <pre> tag
                if not child.tag == moin_page.blockcode and not child.tag == moin_page.code:
                    self.convert_embedded_markup(child)

    def convert_invalid_p_nodes(self, node):
        """
        Processing embedded HTML tags within markup or output from extensions with embedded markup can
        result in invalid HTML output caused by <p> tags enclosing a block element.

        The solution is to search for these occurances and change the <p> tag to a <div>.

        :param node: a tree node
        """
        for child in node:
            if not isinstance(child, str):
                if child.tag == moin_page.p and len(child):
                    for grandchild in child:
                        if not isinstance(grandchild, str) and grandchild.tag in BLOCK_ELEMENTS:
                            child.tag = moin_page.div
                self.convert_invalid_p_nodes(child)

    def __init__(self):
        self.markdown = Markdown(
            extensions=[ExtraExtension(), CodeHiliteExtension(guess_lang=False), "mdx_wikilink_plus", "admonition"],
            extension_configs={
                "mdx_wikilink_plus": {
                    "html_class": None,
                    "image_class": None,
                    "label_case": "none",  # do not automatically CamelCase the label, keep it untouched
                }
            },
        )

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        """
        Convert markdown to moin DOM.

        data is a pointer to an open file (ProtectedRevision object)
        contenttype is likely == 'text/x-markdown;charset=utf-8'
        arguments is not used

        Markdown processing takes place in five steps:

        1. A bunch of "preprocessors" munge the input text.
        2. BlockParser() parses the high-level structural elements of the
           pre-processed text into an ElementTree.
        3. A bunch of "treeprocessors" are run against the ElementTree. One
           such treeprocessor runs InlinePatterns against the ElementTree,
           detecting inline markup.
        4. Some post-processors are run against the ElementTree nodes containing text
            and the ElementTree is converted to an EmeraldTree.
        5. The root of the EmeraldTree is returned.

        """
        # read the data from wiki storage and convert to unicode
        text = decode_data(data, contenttype)

        # Normalize whitespace for consistent parsing. - copied from NormalizeWhitespace in markdown/preprocessors.py
        text = text.replace(md_util.STX, "").replace(md_util.ETX, "")
        text = text.replace("\r\n", "\n").replace("\r", "\n") + "\n\n"
        text = text.expandtabs(self.markdown.tab_length)
        text = re.sub(r"(?<=\n) +\n", "\n", text)

        # save line counts for start of each block, used later for edit autoscroll
        self.count_lines(text)

        # {{{ similar to parts of Markdown 3.0.0 core.py convert method

        # Split into lines and run the line preprocessors.
        lines = text.split("\n")
        for prep in self.markdown.preprocessors:
            lines = prep.run(lines)

        # Parse the high-level elements.
        root = self.markdown.parser.parseDocument(lines).getroot()

        # Run the tree-processors
        for treeprocessor in self.markdown.treeprocessors:
            newRoot = treeprocessor.run(root)
            if newRoot is not None:
                root = newRoot

        # }}} end Markdown 3.0.0 core.py convert method

        add_lineno = bool(flaskg and getattr(flaskg, "add_lineno_attr", False))

        # run markdown post processors and convert from ElementTree to an EmeraldTree object
        converted = self.do_children(root, add_lineno=add_lineno)

        # convert html embedded in text strings to EmeraldTree nodes
        self.convert_embedded_markup(converted)
        # convert P-tags containing block elements to DIV-tags
        self.convert_invalid_p_nodes(converted)

        body = moin_page.body(children=converted)
        root = moin_page.page(children=[body])

        return root


default_registry.register(Converter._factory, Type("text/x-markdown"), type_moin_document)
default_registry.register(Converter._factory, Type("x-moin/format;name=markdown"), type_moin_document)
