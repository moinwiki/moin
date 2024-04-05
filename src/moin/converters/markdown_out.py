# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2018 MoinMoin:RogerHaase - modified moinwiki_out.py for markdown
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Markdown markup output converter

Converts an internal document tree into markdown markup.
"""

import urllib.request
import urllib.parse
import urllib.error

from . import ElementException

from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.utils.iri import Iri

from emeraldtree import ElementTree as ET

from . import default_registry
from moin.utils.mime import Type, type_moin_document


class Markdown:
    """
    Markdown syntax elements
    It's dummy
    """

    h = "#"
    a_open = "<"
    a_desc_open = "("
    a_desc_close = ")"
    a_close = ">"
    comment_open = "<!-- "
    comment_close = " -->"
    verbatim_open = "    "  # * 3
    verbatim_close = "    "  # * 3
    monospace = "`"
    strong = "**"
    emphasis = "*"
    underline_open = "<u>"
    underline_close = "</u>"
    samp_open = "`"
    samp_close = "`"
    stroke_open = "<strike>"
    stroke_close = "</strike>"
    table_marker = "|"
    p = "\n"
    linebreak = "  "
    larger_open = "<big>"
    larger_close = "</big>"
    smaller_open = "<small>"
    smaller_close = "</small>"
    object_open = "{{"
    object_close = "}}"
    definition_list_marker = ":  "
    separator = "----"
    attribute_open = "{: "
    attribute_close = "}"
    # TODO: definition list
    list_type = {
        ("definition", None): "",
        ("ordered", None): "1.",
        ("ordered", "lower-alpha"): "1.",
        ("ordered", "upper-alpha"): "1.",
        ("ordered", "lower-roman"): "1.",
        ("ordered", "upper-roman"): "1.",
        ("unordered", None): "*",
        ("unordered", "no-bullet"): "*",
        (None, None): "::",
    }

    def __init__(self):
        pass


class Converter:
    """
    Converter application/x.moin.document -> text/x.moin.wiki
    """

    namespaces = {moin_page.namespace: "moinpage", xinclude: "xinclude"}

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __init__(self):
        self.list_item_labels = [""]
        self.list_item_label = ""
        self.list_level = 0
        self.footnotes = []  # tuple of (name, text)
        self.footnote_number = 0  # incremented if a footnote name was not passed

    def __call__(self, root):
        self.status = ["text"]
        self.last_closed = None
        self.list_item_label = []
        content = self.open(root)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        if self.footnotes:
            # add footnote definitions to end of content
            notes = []
            for name, txt in self.footnotes:
                notes.append(f"[^{name}]: {txt}")
            notes = "\n".join(notes)
            content += "\n\n" + notes + "\n"
        return content

    def open_children(self, elem, join_char=""):
        childrens_output = []
        for child in elem:
            if isinstance(child, ET.Element):
                # open function can change self.output
                childrens_output.append(self.open(child))
            else:
                ret = ""
                if self.status[-1] == "text":
                    if self.last_closed == "p":
                        ret = "\n"
                if child == "\n" and getattr(elem, "level", 0):
                    child = child + " " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))
                childrens_output.append(f"{ret}{child}")
                self.last_closed = "text"
        out = join_char.join(childrens_output)
        return out

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = "open_" + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        # process odd things like xinclude
        return self.open_children(elem)

    def attribute_list(self, elem):
        """
        Return a string of attributes, in long format: {: id="someid" class="someclass" somekey="some value" }
        """
        attr_list = []
        for key, val in elem.attrib.items():
            if key.name not in ("data-lineno", "outline-level", "href", "item-label-generate", "baseline-shift"):
                attr_list.append(f'{key.name}="{val}"')
        if attr_list:
            return Markdown.attribute_open + " ".join(attr_list) + Markdown.attribute_close
        return ""

    def open_moinpage(self, elem):
        n = "open_moinpage_" + elem.tag.name.replace("-", "_")
        f = getattr(self, n, None)
        if f:
            ret = f(elem)
            if elem.tag.name not in (
                "separator",
                "blockcode",
                "code",
                "div",
                "big",
                "small",
                "sup",
                "sub",
                "th",
                "emphasis",
                "s",
                "ins",
                "u",
                "span",
                "table",
                "a",
            ):
                attrib = self.attribute_list(elem)
                if attrib:
                    if ret.endswith("#\n"):
                        ret = ret[:-1] + " " + attrib + ret[-1:]
                    elif ret.endswith("\n") and not elem.tag.name == "p":
                        ret = ret[:-1] + attrib + ret[-1:]
                    elif ret.endswith("\n") and elem.tag.name == "p":
                        ret += attrib + "\n"
                    else:
                        ret += attrib
            self.last_closed = elem.tag.name.replace("-", "_")
            return ret
        return self.open_children(elem)

    def open_moinpage_a(self, elem):
        """[link text](url "optional title")"""
        href = elem.get(xlink.href, None)
        title = elem.get(html.title_, None)
        if isinstance(href, Iri):
            href = str(href)
        href = href.split("wiki.local:")[-1]
        text = self.open_children(elem)
        if title:
            href = f'{href} "{title}"'
        ret = f"[{text}]({href})"
        cls = elem.get(moin_page.class_)
        if cls:
            ret = ret + '{:class="' + cls + '"}'
        return ret

    def open_moinpage_blockcode(self, elem):
        text = "".join(elem.itertext())

        if elem.attrib.get(html.class_, None) == "codehilite":
            return text

        lines = text.split("\n")
        ret = "\n" + Markdown.verbatim_open + ("\n" + Markdown.verbatim_open).join(lines)
        return "\n" + ret + "\n"

    def open_moinpage_block_comment(self, elem):
        # convert moin hidden comment markdown/html comment: ## some block comment
        return Markdown.comment_open + "\n".join(elem) + Markdown.comment_close

    def open_moinpage_blockquote(self, elem):
        # blockquotes are generated by html_in (and maybe others), not by moinwiki_in
        # to achieve same look, we convert to bulletless unordered list
        ret = self.open_children(elem)
        ret = ret.strip()
        indented = []
        for line in ret.split("\n"):
            indented.append(" > " + line)
        return "\n" + "\n".join(indented) + "\n"

    def open_moinpage_code(self, elem):
        ret = Markdown.monospace
        ret += "".join(elem.itertext())
        ret += Markdown.monospace
        return ret

    def open_moinpage_div(self, elem):
        """
        Find and process div tags with special classes as needed.
        """
        if elem.attrib.get(html.class_, None) == "toc":
            # we do not want expanded toc
            return "\n\n[TOC]\n\n"

        if elem.attrib.get(html.class_, None) == "codehilite" and isinstance(elem[0][1], str):
            # in most cases, codehilite returns plain text blocks; return an indented block
            text = elem[0][1].split("\n")
            return "\n" + "\n".join(["    " + x for x in text]) + "\n"

        childrens_output = self.open_children(elem)
        return "\n\n" + childrens_output + "\n\n"

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return f"{Markdown.emphasis}{childrens_output}{Markdown.emphasis}"

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException("page:outline-level needs to be an integer")
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = Markdown.h * level + " "
        ret += "".join(elem.itertext())
        ret += f" {Markdown.h * level}\n"
        return "\n" + ret

    def open_moinpage_line_break(self, elem):
        return Markdown.linebreak

    def open_moinpage_list(self, elem):
        label_type = elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None)
        self.list_item_labels.append(Markdown.list_type.get(label_type, "*"))
        self.list_level += 1
        ret = ""
        if self.status[-1] != "text" or self.last_closed:
            ret = "\n"
        self.status.append("list")
        self.last_closed = None
        childrens_output = self.open_children(elem)
        list_start = elem.attrib.get(moin_page.list_start)
        if list_start:
            child_out1, child_out2 = childrens_output.split(".", 1)
            childrens_output = f"{child_out1}.#{list_start}{child_out2}"
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        if self.status[-1] == "list":
            ret_end = ""
        else:
            ret_end = "\n"
        return f"{ret}{childrens_output}{ret_end}"

    def open_moinpage_list_item(self, elem):
        self.list_item_label = self.list_item_labels[-1] + " "
        return self.open_children(elem)

    def open_moinpage_list_item_label(self, elem):
        """Used for definition list terms"""
        ret = ""
        if self.list_item_labels[-1] == "" or self.list_item_labels[-1] == Markdown.definition_list_marker:
            self.list_item_labels[-1] = Markdown.definition_list_marker
            self.list_item_label = self.list_item_labels[-1] + " "
            ret = "   " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))
            if self.last_closed:
                ret = f"\n{ret}"
        childrens_output = self.open_children(elem)
        return f"\n{ret}{childrens_output}"

    def open_moinpage_list_item_body(self, elem):
        ret = ""
        if self.last_closed:
            ret = "\n"
        ret += "    " * len(self.list_item_labels[:-2]) + self.list_item_label
        child_out = self.open_children(elem)
        if self.list_item_label[0] == Markdown.definition_list_marker[0]:
            child_out = "\n    ".join(child_out.split("\n"))
        return ret + child_out

    def open_moinpage_note(self, elem):
        # used for moinwiki to markdown conversion; not used for broken markdown to markdown conversion
        class_ = elem.get(moin_page.note_class, "")
        if class_:
            if class_ == "footnote":
                self.footnote_number += 1
                self.footnotes.append((self.footnote_number, self.open_children(elem)))
                return f"[^{self.footnote_number}]"
        # moinwiki footnote placement is ignored; markdown cannot place footnotes in middle of document like moinwiki
        return ""

    def open_moinpage_nowiki(self, elem):
        """No support for moin features like highlight or nowiki within nowiki."""
        if isinstance(elem[0], ET.Element) and elem[0].tag.name == "blockcode" and isinstance(elem[0][0], str):
            text = elem[0][0].split("\n")
            return "\n" + "\n".join(["    " + x for x in text]) + "\n"
        return self.open_children(elem)

    def open_moinpage_object(self, elem):
        """
        Process moinwiki_in objects: {{transclusions}}  and <<Include(parameters,...)>>

        Transcluded objects are expanded in output because Markdown does not support transclusions.
        """
        href = elem.get(xlink.href, elem.get(xinclude.href, ""))
        if isinstance(href, Iri):
            href = str(href)
            href = urllib.parse.unquote(href)
            if href.startswith("/+get/+"):
                href = href.split("/")[-1]
        href = href.split("wiki.local:")[-1]
        if len(elem) and isinstance(elem[0], str):
            # alt text for objects is enclosed within <object...>...</object>
            alt = elem[0]
        else:
            alt = elem.attrib.get(html.alt, "")
        title = elem.attrib.get(html.title_, "")
        if title:
            title = f'"{title}"'
        ret = f"![{alt}]({href} {title})"
        ret = ret.replace(" )", ")")
        return ret

    def open_moinpage_p(self, elem):
        if moin_page.class_ in elem.attrib and "moin-error" in elem.attrib[moin_page.class_]:
            # ignore error messages inserted into DOM
            return ""

        self.status.append("p")
        ret = ""
        if self.status[-2] == "text":
            if self.last_closed == "text":
                ret = Markdown.p * 2 + self.open_children(elem) + Markdown.p
            elif self.last_closed:
                ret = Markdown.p + self.open_children(elem) + Markdown.p
            else:
                ret = self.open_children(elem) + Markdown.p
        elif self.status[-2] == "table":
            if self.last_closed and self.last_closed != "table_cell" and self.last_closed != "table_row":
                ret = Markdown.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-2] == "list":  # TODO: still possible? <p> after <li> removed from moinwiki_in
            if self.last_closed and (
                self.last_closed != "list_item"
                and self.last_closed != "list_item_header"
                and self.last_closed != "list_item_footer"
                and self.last_closed != "list_item_label"
            ):
                ret = Markdown.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        else:
            ret = self.open_children(elem)
        self.status.pop()
        return ret

    def open_moinpage_page(self, elem):
        self.last_closed = None
        if len(self.status) > 1:
            self.status.append("text")
            childrens_output = self.open_children(elem)
            self.status.pop()
            return childrens_output

        self.status.append("text")
        childrens_output = self.open_children(elem)
        self.status.pop()
        return childrens_output

    def open_moinpage_body(self, elem):
        class_ = elem.get(moin_page.class_, "").replace(" ", "/")
        if class_:
            ret = f" {class_}\n"
        elif len(self.status) > 2:
            ret = "\n"
        else:
            ret = ""
        childrens_output = self.open_children(elem)
        return f"{ret}{childrens_output}"

    def open_moinpage_samp(self, elem):
        # text {{{more text}}} end
        ret = Markdown.samp_open
        ret += "".join(elem.itertext())
        ret += Markdown.samp_close
        return ret

    def open_moinpage_separator(self, elem):
        return "\n----\n"

    def open_moinpage_span(self, elem):
        font_size = elem.get(moin_page.font_size, "")
        baseline_shift = elem.get(moin_page.baseline_shift, "")
        if font_size:
            return "{}{}{}".format(
                Markdown.larger_open if font_size == "120%" else Markdown.smaller_open,
                self.open_children(elem),
                Markdown.larger_close if font_size == "120%" else Markdown.smaller_close,
            )
        if baseline_shift == "super":
            return "<sup>{}</sup>".format("".join(elem.itertext()))
        if baseline_shift == "sub":
            return "<sub>{}</sub>".format("".join(elem.itertext()))
        return "".join(self.open_children(elem))

    def open_moinpage_del(self, elem):  # stroke or strike-through
        return Markdown.stroke_open + self.open_children(elem) + Markdown.stroke_close

    def open_moinpage_s(self, elem):  # s is used for stroke or strike by html_in
        return self.open_moinpage_del(elem)

    def open_moinpage_ins(self, elem):  # underline
        return Markdown.underline_open + self.open_children(elem) + Markdown.underline_close

    def open_moinpage_u(self, elem):  # underline via html_in
        return self.open_moinpage_ins(elem)

    def open_moinpage_strong(self, elem):
        return f"{Markdown.strong}{self.open_children(elem)}{Markdown.strong}"

    def open_moinpage_table(self, elem):
        self.status.append("table")
        self.last_closed = None
        ret = self.open_children(elem)
        self.status.pop()
        # markdown tables must have headings
        if "----" not in ret:
            # style: text-align gets lost here
            rows = ret.split("\n")
            header = rows[0][1:-1]  # remove leading and trailing |
            cells = header.split("|")
            marker = Markdown.table_marker + Markdown.table_marker.join(["----" for x in cells]) + Markdown.table_marker
            rows.insert(1, marker)
            ret = "\n".join(rows)
        return "\n" + ret + "\n"

    def open_moinpage_table_header(self, elem):
        # used for reST to moinwiki conversion, maybe others that generate table head
        separator = []
        for th in elem[0]:
            if th.attrib.get(moin_page.style, None) == "text-align: center;":
                separator.append(":----:")
            elif th.attrib.get(moin_page.style, None) == "text-align: left;":
                separator.append(":-----")
            elif th.attrib.get(moin_page.style, None) == "text-align: right;":
                separator.append("-----:")
            else:
                separator.append("------")
        separator = Markdown.table_marker.join(separator)
        ret = self.open_children(elem)
        ret = ret + "{0}{1}{0}\n".format(Markdown.table_marker, separator)
        return ret

    def open_moinpage_table_body(self, elem):
        ret = self.open_children(elem)
        return ret

    def open_moinpage_table_row(self, elem):
        ret = self.open_children(elem, join_char=Markdown.table_marker)
        return "{0}{1}{0}\n".format(Markdown.table_marker, ret)

    def open_moinpage_table_of_content(self, elem):
        return "\n[TOC]\n"

    def open_xinclude(self, elem):
        """Processing of transclusions is similar to objects."""
        return self.open_moinpage_object(elem)


default_registry.register(Converter._factory, type_moin_document, Type("text/x-markdown"))
default_registry.register(Converter._factory, type_moin_document, Type("x-moin/format;name=markdown"))
