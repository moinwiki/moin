# Copyright: 2008-2010 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Markdown input converter.

https://daringfireball.net/projects/markdown/
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import re

from html.entities import name2codepoint
from collections import deque

from moin.utils.tree import moin_page, xml, html, xlink, xinclude
from ._util import decode_data, sanitise_uri_scheme
from moin.utils.iri import Iri
from moin.converters import html_in
from flask import current_app

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

from moin import log
from moin.utils.mime import Type, type_moin_document

from . import default_registry

if TYPE_CHECKING:
    from moin.converters._args import Arguments
    from typing_extensions import Self

logging = log.getLogger(__name__)

html_in_converter = html_in.Converter()
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


class Converter(html_in.HtmlTags):
    """
    Convert Markdown -> .x.moin.document.

    Also handle HTML tags that are supported by Moin.
    """

    # {{{ html conversion

    # HTML tags that can be converted into a DOM tag without additional attributes
    # The html_in converter uses specific methods for <dl> and <table> but we keep it simple here
    simple_tags = html_in.Converter.simple_tags.copy()
    simple_tags["dl"] = moin_page.list_item
    simple_tags["table"] = moin_page.table

    # Non-void HTML tags that could be split by markdown's inline pattern processor
    _non_void_html_tags = frozenset(
        html_in.HtmlTags.symmetric_tags
        | (set(simple_tags.keys()) - {"br"})
        | set(html_in.HtmlTags.indirect_tags.keys())
    )
    _open_tag_re = re.compile(r"^(.*?)<(\w+)(?:\s[^>]*)?>(.*)$", re.DOTALL)

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
        key = xlink.href
        attrib = {}
        if self.base_url:
            attrib[key] = "".join([self.base_url, element.get(html.data)])
        else:
            attrib[key] = element.get(html.data)

        # Convert the href attribute into unicode
        attrib[key] = str(attrib[key])
        return moin_page.object(attrib)

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
        attrib = {}
        if element.attrib.get("title"):
            attrib[html.title_] = element.attrib.get("title")
        href = postproc_text(self.markdown, element.attrib.get("href"))
        # ensure a safe scheme, fall back to wiki-internal reference:
        attrib[xlink.href] = sanitise_uri_scheme(href)
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
        except (AssertionError, IndexError) as ex:
            # malformed tags, will be escaped so user can see and fix
            logging.debug(f"Caught exception in embedded_markup: {ex}")
            return text

    def convert_embedded_markup(self, node):
        """
        Recurse through tree looking for embedded or generated markup.

        :param node: a tree node
        """
        for idx, child in enumerate(node):
            if isinstance(child, str):
                # search for HTML tags
                if re.search("<[^ ].*?>", child):
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

    def _create_element_for_tag(self, tag_name, children):
        """Create a moin_page DOM element for the given HTML tag name."""
        if tag_name in self.symmetric_tags:
            return ET.Element(ET.QName(tag_name, moin_page), attrib={}, children=children)
        elif tag_name in self.simple_tags:
            return ET.Element(self.simple_tags[tag_name], attrib={}, children=children)
        elif tag_name in self.indirect_tags:
            attrib = {moin_page("html-tag"): tag_name}
            return ET.Element(self.indirect_tags[tag_name], attrib=attrib, children=children)
        else:
            return ET.Element(ET.QName(tag_name, moin_page), attrib={}, children=children)

    def _reassemble_split_html_tags(self, node):
        """
        Reassemble raw HTML tags split by markdown's inline pattern processor.

        When markdown converts inline syntax (like _emphasis_) inside HTML tags
        (like <del>), the HTML tag gets split across text/tail boundaries.
        This results in separate strings for opening and closing tags with
        converted elements in between:
            ["<del>text ", Element(emphasis, ...), "</del>"]

        This method detects such splits and reassembles them into proper DOM elements:
            [Element(del, ["text ", Element(emphasis, ...)])]
        """
        if isinstance(node, list):
            children = node
        else:
            children = list(node)

        result = []
        i = 0
        changed = False

        while i < len(children):
            child = children[i]
            if isinstance(child, str):
                m = self._open_tag_re.match(child)
                if m:
                    pre_text, tag_name, inner_text = m.group(1), m.group(2), m.group(3)
                    tag_lower = tag_name.lower()
                    closing_tag = f"</{tag_name}>"

                    if tag_lower in self._non_void_html_tags and closing_tag not in child:
                        # Scan forward through siblings for the matching closing tag
                        close_idx = None
                        for j in range(i + 1, len(children)):
                            sibling = children[j]
                            if isinstance(sibling, str) and closing_tag in sibling:
                                close_idx = j
                                break

                        if close_idx is not None:
                            changed = True
                            close_str = children[close_idx]
                            close_pos = close_str.index(closing_tag)
                            inner_tail = close_str[:close_pos]
                            post_text = close_str[close_pos + len(closing_tag) :]

                            # Collect inner children
                            inner = []
                            if inner_text:
                                inner.append(inner_text)
                            for k in range(i + 1, close_idx):
                                inner.append(children[k])
                            if inner_tail:
                                inner.append(inner_tail)

                            # Recursively process inner children (handles nested split tags)
                            self._reassemble_split_html_tags(inner)

                            new_elem = self._create_element_for_tag(tag_lower, inner)

                            if pre_text:
                                result.append(pre_text)
                            result.append(new_elem)
                            if post_text:
                                result.append(post_text)

                            i = close_idx + 1
                            continue

                result.append(child)
                i += 1
            else:
                # Recurse into element children
                self._reassemble_split_html_tags(child)
                result.append(child)
                i += 1

        if changed:
            if isinstance(node, list):
                node[:] = result
            else:
                # EmeraldTree Element: replace all children
                del node[:]
                for c in result:
                    node.append(c)

    def __init__(self):
        # The Moin configuration
        self.app_configuration = current_app.cfg

        self.markdown = Markdown(
            extensions=[ExtraExtension(), CodeHiliteExtension(guess_lang=False), "mdx_wikilink_plus", "admonition"]
            + self.app_configuration.markdown_extensions,
            extension_configs={
                "mdx_wikilink_plus": {
                    "html_class": None,
                    "image_class": None,
                    "label_case": "none",  # do not automatically CamelCase the label, keep it untouched
                }
            },
        )

    @classmethod
    def _factory(cls, input: Type, output: Type, **kwargs: Any) -> Self:
        return cls()

    def __call__(self, data: Any, contenttype: str | None = None, arguments: Arguments | None = None) -> Any:
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

        # reassemble HTML tags that were split by markdown's inline pattern processor
        self._reassemble_split_html_tags(converted)

        # convert html embedded in text strings to EmeraldTree nodes
        self.convert_embedded_markup(converted)
        # convert P-tags containing block elements to DIV-tags
        self.convert_invalid_p_nodes(converted)

        body = moin_page.body(children=converted)
        root = moin_page.page(children=[body])

        return root


default_registry.register(Converter._factory, Type("text/x-markdown"), type_moin_document)
default_registry.register(Converter._factory, Type("x-moin/format;name=markdown"), type_moin_document)
