# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Moinwiki markup output converter

Converts an internal document tree into moinwiki markup.
"""

import urllib.request
import urllib.parse
import urllib.error
from re import findall, sub

from emeraldtree import ElementTree as ET
from markupsafe import Markup

from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.utils.iri import Iri
from moin.utils.mime import Type, type_moin_document, type_moin_wiki

from moin.macros import modules as macro_modules
from . import ElementException
from . import default_registry

from moin import log

logging = log.getLogger(__name__)


class Moinwiki:
    """
    Moinwiki syntax elements
    It's dummy
    """

    h = "="
    a_open = "[["
    a_separator = "|"
    a_close = "]]"
    verbatim_open = "{"  # * 3
    verbatim_close = "}"  # * 3
    monospace = "`"
    strong = "'''"
    emphasis = "''"
    underline = "__"
    samp_open = "{{{"  # 3 brackets is only option for inline
    samp_close = "}}}"
    stroke_open = "--("
    stroke_close = ")--"
    table_marker = "||"
    p = "\n"
    linebreak = "<<BR>>"
    larger_open = "~+"
    larger_close = "+~"
    smaller_open = "~-"
    smaller_close = "-~"
    object_open = "{{"
    object_close = "}}"
    definition_list_marker = "::"
    separator = "----"
    # TODO: definition list
    list_type = {
        ("definition", None): "",
        ("ordered", None): "1.",
        ("ordered", "lower-alpha"): "a.",
        ("ordered", "upper-alpha"): "A.",
        ("ordered", "lower-roman"): "i.",
        ("ordered", "upper-roman"): "I.",
        ("unordered", None): "*",
        ("unordered", "no-bullet"): ".",
        (None, None): "::",
    }

    def __init__(self):
        pass


class Converter:
    """
    Converter application/x.moin.document -> text/x.moin.wiki
    """

    namespaces = {moin_page.namespace: "moinpage", xinclude: "xinclude"}

    supported_tag = {
        "moinpage": (
            "a",
            "blockcode",
            "break_line",
            "code",
            "div",
            "emphasis",
            "h",
            "list",
            "list_item",
            "list_item_label",
            "list_item_body",
            "nowiki",
            "p",
            "page",
            "separator",
            "span",
            "strong",
            "object",
            "table",
            "table_header",
            "table_footer",
            "table_body",
            "table_row",
            "table_cell",
        ),
        "xinclude": ("include",),
    }

    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __init__(self):

        # TODO: create class containing all table attributes
        self.table_tableclass = ""
        self.table_tablestyle = ""
        self.table_rowsclass = ""
        self.table_rowsstyle = ""
        self.table_rowstyle = ""
        self.table_rowclass = ""

        self.list_item_labels = [""]
        self.list_item_label = ""
        self.list_level = 0
        self.unknown_macro_list = []

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list - <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of differences in interpretation of <p> in different places

    def __call__(self, root):
        self.status = ["text"]
        self.last_closed = None
        self.list_item_label = []
        content = self.open(root)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        content = content[1:] if content.startswith("\n") else content
        return content

    def open_children(self, elem):
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
        out = "".join(childrens_output)
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

    def open_moinpage(self, elem):
        n = "open_moinpage_" + elem.tag.name.replace("-", "_")
        f = getattr(self, n, None)
        if f:
            ret = f(elem)
            self.last_closed = elem.tag.name.replace("-", "_")
            return ret
        return self.open_children(elem)

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)
        params = {}
        params["target"] = elem.get(html.target, None)
        params["title"] = elem.get(html.title_, None)
        params["download"] = elem.get(html.download, None)
        params["class"] = elem.get(html.class_, None)
        params["accesskey"] = elem.get(html.accesskey, None)
        # we sort so output order is predictable for tests
        params = ",".join([f'{p}="{params[p]}"' for p in sorted(params) if params[p]])

        # XXX: We don't have Iri support for now
        if isinstance(href, Iri):
            href = str(href)
        # TODO: this can be done using one regex, can it?
        href = href.split("#")
        if len(href) > 1:
            href, fragment = href
        else:
            href, fragment = href[0], ""
        href = href.split("?")
        args = ""
        if len(href) > 1:
            # With normal
            args = "".join(["&" + s for s in findall(r"(?:^|;|,|&|)(\w+=\w+)(?:,|&|$|)", href[1])])
        href = href[0].split("wiki.local:")[-1]
        if args:
            args = "?" + args[1:]
        if fragment:
            args += "#" + fragment
        text = self.open_children(elem)
        if text == href:
            text = ""
        ret = f"{href}{args}|{text}|{params}"
        ret = ret.rstrip("|")
        if ret.startswith("wiki://"):
            # interwiki fixup
            ret = ret[7:]
            ret = ret.replace("/", ":", 1)
        return Moinwiki.a_open + ret + Moinwiki.a_close

    def open_moinpage_blockcode(self, elem):
        text = "".join(elem.itertext())
        max_subpage_lvl = 3
        for s in findall(r"}+", text):
            if max_subpage_lvl <= len(s):
                max_subpage_lvl = len(s) + 1
        ret = f"{Moinwiki.verbatim_open * max_subpage_lvl}\n{text}\n{Moinwiki.verbatim_close * max_subpage_lvl}\n"
        return "\n" + ret + "\n"

    def open_moinpage_block_comment(self, elem):
        # text child similar to: ## some block comment
        return "\n\n" + "\n".join(elem) + "\n\n"

    def open_moinpage_blockquote(self, elem):
        # blockquotes are generated by html_in (and maybe others), not by moinwiki_in
        # to achieve same look, we convert to bulletless unordered list
        ret = self.open_children(elem)
        ret = ret.strip()
        ret = ret.replace("\n\n", "\n\n    . ")
        ret = ret.split("<<BR>>")
        indented = []
        for line in ret:
            indented.append("    . " + line)
        return "\n\n" + "\n".join(indented) + "\n\n"

    def open_moinpage_code(self, elem):
        ret = Moinwiki.monospace
        ret += "".join(elem.itertext())
        ret += Moinwiki.monospace
        return ret

    def open_moinpage_div(self, elem):
        childrens_output = self.open_children(elem)
        return "\n\n" + childrens_output + "\n\n"

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return f"{Moinwiki.emphasis}{childrens_output}{Moinwiki.emphasis}"

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
        ret = Moinwiki.h * level + " "
        ret += "".join(elem.itertext())
        ret += f" {Moinwiki.h * level}\n"
        return "\n" + ret

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    def open_moinpage_list(self, elem):
        label_type = elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None)
        self.list_item_labels.append(Moinwiki.list_type.get(label_type, ""))
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
        ret = ""
        if self.list_item_labels[-1] == "" or self.list_item_labels[-1] == Moinwiki.definition_list_marker:
            self.list_item_labels[-1] = Moinwiki.definition_list_marker
            self.list_item_label = self.list_item_labels[-1] + " "
            ret = " " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))  # self.list_level
            if self.last_closed:
                ret = f"\n{ret}"
        childrens_output = self.open_children(elem)
        return f"{ret}{childrens_output}{Moinwiki.definition_list_marker}"

    def open_moinpage_list_item_body(self, elem):
        ret = ""
        if self.last_closed:
            ret = "\n"
        ret += " " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1])) + self.list_item_label
        return ret + self.open_children(elem)

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, "")
        if class_:
            if class_ == "footnote":
                return f"<<FootNote({self.open_children(elem)})>>"
        return "\n<<FootNote()>>\n"

    def open_moinpage_nowiki(self, elem):
        """{{{#!wiki ... or {{{#!highlight ... etc."""
        nowiki_marker_len, all_nowiki_args, content = elem._children
        try:
            nowiki_args = all_nowiki_args[0]
        except IndexError:
            # this happens only with pytest, why wasn't open_moinpage_blockcode called?
            nowiki_args = ""
        nowiki_marker_len = int(nowiki_marker_len)
        return (
            "\n"
            + Moinwiki.verbatim_open * nowiki_marker_len
            + f"{nowiki_args}\n{content}\n"
            + Moinwiki.verbatim_close * nowiki_marker_len
            + "\n"
        )

    def include_object(self, xpointer, href):
        """
        Return a properly formatted include macro.

        xpointer similar to: 'xmlns(page=http://moinmo.in/namespaces/page) page:include(heading(my title) level(2))'
        TODO: xpointer format is ugly, Arguments class would be easier to use here.

        The moin2 include macro (per include.py) supports:
            pages (pagename), sort, items, skipitems, heading, and level.

        If incoming href == '', then there will be a pages value similar to '^^ma' that needs to be unescaped.
        TODO: some 1.9 features have been dropped.
        """
        arguments = {}
        href = href.split(":")[-1]
        args = xpointer.split("page:include(")[1][:-1]
        args = args[:-1].split(") ")
        for arg in args:
            key, val = arg.split("(")
            arguments[key] = val
        parms = f",{arguments.get('heading', '')},{arguments.get('level', '')}"
        for key in ("sort", "items", "skipitems"):
            if key in arguments:
                parms += f',{key}="{arguments[key]}"'
        while parms.endswith(","):
            parms = parms[:-1]
        if not href and "pages" in arguments:
            # xpointer needs unescaping, see comments above
            href = arguments["pages"].replace("^(", "(").replace("^)", ")").replace("^^", "^")
        return f"<<Include({href}{parms})>>"

    def open_moinpage_object(self, elem):
        """
        Process objects: {{transclusions}}  and <<Include(parameters,...)>>

        Other macros are processes by open_moinpage_part.
        """
        href = elem.get(xlink.href, elem.get(xinclude.href, ""))
        if isinstance(href, Iri):
            href = str(href)
            href = urllib.parse.unquote(href)

        try:
            return self.include_object(elem.attrib[xinclude.xpointer], href)
        except KeyError:
            pass

        href = href.split("?")
        args = ""
        if len(href) > 1:
            args = " ".join([s for s in findall(r"(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)", href[1]) if s[:3] != "do="])
        href = href[0].split("wiki.local:")[-1]

        if len(elem) and isinstance(elem[0], str):
            # alt text for objects is enclosed within <object...>...</object>
            alt = elem[0]
        else:
            alt = elem.attrib.get(html.alt, "")

        whitelist = {html.width: "width", html.height: "height", html.class_: "class"}
        options = []
        for attr, value in sorted(elem.attrib.items()):
            if attr in whitelist.keys():
                options.append(f'{whitelist[attr]}="{value}"')

        if args:
            args = "&" + args
        if options:
            if args:
                args += " "
            args += " ".join(options)

        ret = f"{Moinwiki.object_open}{href}|{alt}|{args}{Moinwiki.object_close}"
        ret = sub(r"\|+}}", "}}", ret)
        return ret

    def open_moinpage_p(self, elem):
        if moin_page.class_ in elem.attrib and "moin-error" in elem.attrib[moin_page.class_]:
            # ignore error messages inserted into DOM
            return ""

        self.status.append("p")
        ret = ""
        if self.status[-2] == "text":
            if self.last_closed == "text":
                ret = Moinwiki.p * 2 + self.open_children(elem) + Moinwiki.p
            elif self.last_closed:
                ret = Moinwiki.p + self.open_children(elem) + Moinwiki.p
            else:
                ret = self.open_children(elem) + Moinwiki.p
        elif self.status[-2] == "table":
            if self.last_closed and self.last_closed != "table_cell" and self.last_closed != "table_row":
                ret = Moinwiki.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-2] == "list":  # TODO: still possible? <p> after <li> removed from moinwiki_in
            if self.last_closed and (
                self.last_closed != "list_item"
                and self.last_closed != "list_item_header"
                and self.last_closed != "list_item_footer"
                and self.last_closed != "list_item_label"
            ):
                ret = Moinwiki.linebreak + self.open_children(elem)
            else:
                ret = self.open_children(elem)
        else:
            ret = self.open_children(elem)
        self.status.pop()
        return ret

    def open_moinpage_page(self, elem):
        self.last_closed = None
        ret = ""
        if len(self.status) > 1:
            ret = "#!wiki"
            max_subpage_lvl = 3
            self.status.append("text")
            childrens_output = self.open_children(elem)
            self.status.pop()
            for s in findall(r"}+", childrens_output):
                if max_subpage_lvl <= len(s):
                    max_subpage_lvl = len(s) + 1
            return "{}{}{}{}\n".format(
                Moinwiki.verbatim_open * max_subpage_lvl,
                ret,
                childrens_output,
                Moinwiki.verbatim_close * max_subpage_lvl,
            )

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

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, "").split(";")
        if len(type) == 2:
            if type[0] == "x-moin/macro":
                name = type[1].split("=")[1]
                if name not in macro_modules:
                    logging.debug(f"Unknown macro {name} found.")
                    if name not in self.unknown_macro_list:
                        self.unknown_macro_list.append(name)
                eol = "\n\n" if elem.tag.name == "part" else ""
                if len(elem) and elem[0].tag.name == "arguments":
                    return "{0}<<{1}({2})>>{0}".format(eol, name, elem[0][0])
                else:
                    return "{0}<<{1}()>>{0}".format(eol, name)
            elif type[0] == "x-moin/format":
                elem_it = iter(elem)
                ret = f"{{{{{{#!{type[1].split('=')[1]}"
                if len(elem) and next(elem_it).tag.name == "arguments":
                    args = []
                    for arg in next(iter(elem)):
                        if arg.tag.name == "argument":
                            args.append(f"{arg.get(moin_page.name, '')}=\"{' '.join(arg.itertext())}\"")
                    ret = f"{ret}({' '.join(args)})"
                    elem = next(elem_it)
                ret = f"{ret}\n{' '.join(elem.itertext())}\n}}}}}}\n"
                return ret
        return Markup.unescape(elem.get(moin_page.alt, "")) + "\n"

    def open_moinpage_inline_part(self, elem):
        ret = self.open_moinpage_part(elem)
        if ret[-1] == "\n":
            ret = ret[:-1]
        return ret

    def open_moinpage_samp(self, elem):
        # text {{{more text}}} end
        ret = Moinwiki.samp_open
        ret += "".join(elem.itertext())
        ret += Moinwiki.samp_close
        return ret

    def open_moinpage_separator(self, elem, hr_class_prefix="moin-hr"):
        hr_ending = "\n"
        hr_class = elem.attrib.get(moin_page("class"))
        if hr_class:
            try:
                height = int(hr_class.split(hr_class_prefix)[1]) - 1
            except (ValueError, IndexError, TypeError):
                raise ElementException(f"page:separator has invalid class {hr_class}")
            else:
                if 0 <= height <= 5:
                    hr_ending = ("-" * height) + hr_ending
        return Moinwiki.separator + hr_ending

    def open_moinpage_span(self, elem):
        # moin syntax does not support style attributes within span tags.
        # Colored text or backgrounds supported by html, markdown extensions, etc
        # are ignored and not converted.
        font_size = elem.get(moin_page.font_size, "")
        baseline_shift = elem.get(moin_page.baseline_shift, "")
        class_ = elem.get(moin_page.class_, "")
        if class_ == "comment":
            return f"/* {self.open_children(elem)} */"
        if font_size:
            return "{}{}{}".format(
                Moinwiki.larger_open if font_size == "120%" else Moinwiki.smaller_open,
                self.open_children(elem),
                Moinwiki.larger_close if font_size == "120%" else Moinwiki.smaller_close,
            )
        if baseline_shift == "super":
            return f"^{''.join(elem.itertext())}^"
        if baseline_shift == "sub":
            return f",,{''.join(elem.itertext())},,"
        return "".join(self.open_children(elem))

    def open_moinpage_del(self, elem):  # stroke or strike-through
        return Moinwiki.stroke_open + self.open_children(elem) + Moinwiki.stroke_close

    def open_moinpage_s(self, elem):  # s is used for stroke or strike by html_in
        return self.open_moinpage_del(elem)

    def open_moinpage_ins(self, elem):  # underline
        return Moinwiki.underline + self.open_children(elem) + Moinwiki.underline

    def open_moinpage_u(self, elem):  # underline via html_in
        return self.open_moinpage_ins(elem)

    def open_moinpage_strong(self, elem):
        return f"{Moinwiki.strong}{self.open_children(elem)}{Moinwiki.strong}"

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get(moin_page.class_, "")
        # moin-wiki-table class was added by moinwiki_in so html_out can convert multiple body's into head, foot
        self.table_tableclass = self.table_tableclass.replace("moin-wiki-table", "").strip()
        self.table_tablestyle = elem.attrib.get(moin_page.style, "")
        if elem[0].tag == moin_page.caption:
            self.table_caption = elem[0][0]
        else:
            self.table_caption = ""
        self.table_rowsstyle = ""
        self.table_rowsclass = ""
        self.table_multi_body = ""
        self.status.append("table")
        self.last_closed = None
        ret = self.open_children(elem)
        self.status.pop()
        return "\n" + ret + "\n"

    def open_moinpage_caption(self, elem):
        # return empty string, text has already been processed in open_moinpage_table above
        return ""

    def open_moinpage_table_header(self, elem):
        # used for reST to moinwiki conversion, maybe others that generate table head
        ret = self.open_children(elem)
        return ret + "=====\n"

    def open_moinpage_table_footer(self, elem):
        # no known use, need some markup that generates table foot
        ret = self.open_children(elem)
        return "=====\n" + ret

    def open_moinpage_table_body(self, elem):
        self.table_rowsclass = ""
        ret = self.table_multi_body + self.open_children(elem)
        # multible body elements separate header/body/footer within DOM created by moinwiki_in
        self.table_multi_body = "=====\n"
        return ret

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get(moin_page.class_, "")
        self.table_rowclass = " ".join([s for s in [self.table_rowsclass, self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get(moin_page.style, "")
        self.table_rowstyle = " ".join([s for s in [self.table_rowsstyle, self.table_rowstyle] if s])
        ret = self.open_children(elem)
        self.table_rowstyle = ""
        self.table_rowclass = ""
        return ret + Moinwiki.table_marker + "\n"

    def open_moinpage_th(self, elem):
        return self.open_moinpage_table_cell_head(self, elem)

    def open_moinpage_table_cell_head(self, elem):
        return self.open_moinpage_table_cell(elem)

    def open_moinpage_td(self, elem):
        return self.open_moinpage_table_cell(self, elem)

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get(moin_page.class_, "")
        table_cellstyle = elem.attrib.get(moin_page.style, "")
        number_columns_spanned = int(elem.get(moin_page.number_columns_spanned, 1))
        number_rows_spanned = elem.get(moin_page.number_rows_spanned, None)
        ret = Moinwiki.table_marker
        attrib = []

        # TODO: maybe this can be written shorter
        if self.table_tableclass:
            attrib.append(f'tableclass="{self.table_tableclass}"')
            self.table_tableclass = ""
        if self.table_tablestyle:
            attrib.append(f'tablestyle="{self.table_tablestyle}"')
            self.table_tablestyle = ""
        if self.table_caption:
            attrib.append(f'caption="{self.table_caption}"')
            self.table_caption = ""
        if self.table_rowclass:
            attrib.append(f'rowclass="{self.table_rowclass}"')
            self.table_rowclass = ""
        if self.table_rowstyle:
            attrib.append(f'rowstyle="{self.table_rowstyle}"')
            self.table_rowstyle = ""
        if table_cellclass:
            attrib.append(f'class="{table_cellclass}"')
        if table_cellstyle:
            attrib.append(f'style="{table_cellstyle}"')
        if number_rows_spanned:
            attrib.append(f'rowspan="{number_rows_spanned}"')
        if number_columns_spanned > 1:
            attrib.append(f'colspan="{number_columns_spanned}"')

        attrib = " ".join(attrib)

        if attrib:
            ret += f"<{attrib}>"
        childrens_output = self.open_children(elem)
        return ret + childrens_output

    def open_moinpage_table_of_content(self, elem):
        return f"<<TableOfContents({elem.get(moin_page.outline_level, '')})>>\n"

    def open_xinclude(self, elem):
        """Processing of transclusions is similar to objects."""
        return self.open_moinpage_object(elem)


default_registry.register(Converter.factory, type_moin_document, type_moin_wiki)
default_registry.register(Converter.factory, type_moin_document, Type("x-moin/format;name=wiki"))
