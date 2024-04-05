# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - reStructuredText markup output converter

Converts an internal document tree into reStructuredText markup.

This converter based on ReStructuredText 2006-09-22.
"""

import re

from emeraldtree import ElementTree as ET

from . import ElementException

from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import html, moin_page, xlink, xinclude
from moin.utils.iri import Iri

from . import default_registry


class Cell:

    def __init__(self, text):
        self.text = text

    def __call__(self):
        return self.text

    def height(self):
        return len(self.text.split("\n"))

    def width(self):
        max = 0
        for i in self.text.split("\n"):
            if len(i) > max:
                max = len(i)
        return max


class Table:
    """
    An object of this class collects the structure of a table
    and represent it in ReStructuredText syntax.
    """

    def __init__(self):
        self.i = -1
        self.j = -1
        self.table = []
        self.header_count = 0
        self.rowclass = ""

    def add_row(self):
        """
        Add new row to the table.
        """
        if self.rowclass == "table-header":
            self.header_count += 1
        row = []
        self.i += 1
        self.j = 0
        self.table.append(row)
        if self.i > 0:
            if len(self.table[-2]) > self.j:
                self.add_cell(self.table[-2][self.j][0], self.table[-2][self.j][1] - 1, Cell(""))
        return row

    def end_row(self):
        """
        Adds empty cells to current row if it's too short.

        Moves the row to the head of the table if it is table header.
        """
        if len(self.table) > 1:
            if len(self.table[-2]) > len(self.table[-1]):
                self.add_cell(1, 1, Cell(""))
                self.end_row()
            if self.rowclass == "table-header":
                self.table.insert(self.header_count - 1, self.table.pop())

    def add_cell(self, cs, rs, cell):
        """
        Adds cell to the row.

        :param cs: number of columns spanned
        """
        if cs < 1 or rs < 1:
            return
        self.table[-1].append((cs, rs, cell))
        for i in range(cs - 1):
            self.table[-1].append((cs - i - 1, rs, Cell("")))
        self.j += cs
        if self.i > 0:
            if len(self.table[-2]) > self.j:
                self.add_cell(self.table[-2][self.j][0], self.table[-2][self.j][1] - 1, Cell(""))
        return

    def height(self):
        """
        :returns: number of rows in the table
        """
        return len(self.table)

    def width(self):
        """
        :returns: width of rows in the table or zero if rows have different width
        """
        if not self.table:
            return 0
        width = len(self.table[0])
        for row in self.table:
            if len(row) != width:
                return 0
        return width

    def col_width(self, col):
        """
        Counts the width of the column in ReSturcturedText representation.

        :param col: index of the column
        :returns: number of characters
        """
        if self.width() <= col:
            return 0
        width = 0
        for row in self.table:
            if row[col][2].width() > width:
                width = row[col][2].width()
        return width

    def row_height(self, row):
        """
        Counts lines in ReSturcturedText representation of the row

        :param row: index of the row
        :returns: number of lines
        """
        if self.height() <= row:
            return 0
        height = 0
        for col in self.table[row]:
            if col[2].height() > height:
                height = col[2].height()
        return height

    def __repr__(self):
        """
        Represent table using ReStructuredText syntax.
        """
        ret = []
        if self.height() and self.width():
            cols = []
            rows = []
            row = self.table[0]
            for col in range(self.width()):
                cols.append(self.col_width(col))
            for row in range(self.height()):
                rows.append(self.row_height(row))
            ret = []
            line = ["+"]
            row = self.table[0]
            for col in range(len(cols)):
                line.append("-" * cols[col])
                if self.table[0][col][0] > 1:
                    line.append("-")
                else:
                    line.append("+")
            ret.append("".join(line))
            for row in range(len(rows)):
                for i in range(rows[row]):
                    line = []
                    line.append("|")
                    for col in range(len(cols)):
                        if self.table[row][col][2].height() <= i:
                            line.append("".ljust(cols[col])[: cols[col]])
                        else:
                            line.append(self.table[row][col][2]().split("\n")[i].ljust(cols[col])[: cols[col]])
                        if self.table[row][col][0] > 1:
                            line.append(" ")
                        else:
                            line.append("|")

                    ret.append("".join(line))
                line = ["+"]
                for col in range(len(cols)):
                    if self.table[row][col][1] > 1:
                        line.append(" " * cols[col])
                    elif row == self.header_count - 1:
                        line.append("=" * cols[col])
                    else:
                        line.append("-" * cols[col])
                    if self.table[row][col][0] > 1:
                        if row + 1 < len(rows) and self.table[row + 1][col][0] > 1 or row + 1 >= len(rows):
                            line.append("-")
                        else:
                            line.append("+")
                    else:
                        line.append("+")
                ret.append("".join(line))
        return "\n".join(ret)


class ReST:
    """
    reST syntax elements
    """

    # moin2 reST standard headings, uses = above and below h1, = below h2, - below h3... + below h6
    # these heading styles are used in all .rst files under /docs/
    # does not agree with: http://documentation-style-guide-sphinx.readthedocs.io/en/latest/style-guide.html#headings
    h_top = " =     "
    h_bottom = " ==-*:+"

    a_separator = "|"
    verbatim = "::"
    monospace = "``"
    strong = "**"
    emphasis = "*"
    p = "\n"
    linebreak = "\n\n"
    separator = "----"
    list_type = {
        ("definition", None): "",
        ("ordered", None): "1.",
        ("ordered", "lower-alpha"): "a.",
        ("ordered", "upper-alpha"): "A.",
        ("ordered", "lower-roman"): "i.",
        ("ordered", "upper-roman"): "I.",
        ("unordered", None): "*",
        (None, None): " ",
    }


class Converter:
    """
    Converter application/x.moin.document -> text/x.moin.rst
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
            "p",
            "page",
            "separator",
            "span",
            "strong",
            "object",
            "table",
            "table_header",
            "teble_footer",
            "table_body",
            "table_row",
            "table_cell",
        )
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

        self.list_item_labels = []
        self.list_item_label = ""
        self.list_level = -1

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list -
        #       <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of
        #  differences in interpretation of <p> in different places

    def __call__(self, root):
        self.status = ["text"]
        self.last_closed = None
        self.list_item_label = []
        self.footnotes = []
        self.objects = []
        self.headings = []
        self.all_used_references = []
        self.anonymous_reference = None
        self.used_references = []
        self.delete_newlines = False
        self.line_block_indent = -4
        ret = self.open(root)
        notes = "\n\n".join(".. [#] {}".format(note.replace("\n", "\n  ")) for note in self.footnotes)
        if notes:
            return ret + self.define_references() + f"\n\n{notes}\n\n"

        return ret + self.define_references()

    def open_children(self, elem):
        childrens_output = []
        self.delete_newlines = False
        delete_newlines = False
        for child in elem:
            if isinstance(child, ET.Element):
                childs_output = self.open(child)
                if self.delete_newlines:
                    while childrens_output and re.match(r"(\n*)\Z", childrens_output[-1]):
                        childrens_output.pop()
                    if childrens_output:
                        last_newlines = r"(\n*)\Z"
                        i = -len(re.search(last_newlines, childrens_output[-1]).groups(1)[0])
                        if i:
                            childrens_output[-1] = childrens_output[-1][:i]
                    else:
                        delete_newlines = True
                self.delete_newlines = False
                childrens_output.append(childs_output)
            else:
                if self.status[-1] == "table":
                    if self.last_closed == "p":
                        childrens_output.append("\n\n")
                elif self.status[-1] == "list":
                    child = re.sub(
                        r"\n(.)",
                        lambda m: "\n{}{}".format(
                            " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)
                        ),
                        child,
                    )
                    if self.last_closed == "p":
                        childrens_output.append(
                            "\n" + " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels))
                        )
                elif self.status[-1] == "text":
                    if self.last_closed == "p":
                        childrens_output.append(self.define_references())
                        childrens_output.append("\n")
                elif self.status[-2] == "list":
                    child = re.sub(
                        r"\n(.)",
                        lambda m: "\n{}{}".format(
                            " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)
                        ),
                        child,
                    )
                childrens_output.append(child)
                self.last_closed = "text"
        self.delete_newlines = delete_newlines
        return "".join(childrens_output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = "open_" + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return self.open_children(elem)

    def open_moinpage(self, elem):
        n = "open_moinpage_" + elem.tag.name.replace("-", "_")
        f = getattr(self, n, None)
        if f:
            ret = f(elem)
            self.last_closed = elem.tag.name.replace("-", "_")
            return ret
        return self.open_children(elem)

    def open_xinclude(self, elem):
        n = "open_xinclude_" + elem.tag.name.replace("-", "_")
        f = getattr(self, n, None)
        if f:
            ret = f(elem)
            self.last_closed = elem.tag.name.replace("-", "_")
            return ret
        return self.open_children(elem)

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)
        text = "".join(elem.itertext()).replace("\n", " ")
        # TODO: check that links have different alt texts
        if text in [t for (t, h) in self.all_used_references]:
            if (text, href) in self.all_used_references:
                return f"`{text}`_"
            if not self.anonymous_reference:
                self.anonymous_reference = href
                self.used_references.insert(0, ("_", href))
                return f"`{text}`__"
            else:
                while text in [t for (t, h) in self.all_used_references]:
                    text += "~"
        self.used_references.append((text, href))
        return f"`{text}`_"

    def open_moinpage_blockcode(self, elem):
        text = "".join(elem.itertext())
        text = text.replace("\n", "\n  " + " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)))
        if self.list_level >= 0:
            self.delete_newlines = True
        return "\n::\n\n  {}{}\n\n".format(
            " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)), text
        )

    def open_moinpage_code(self, elem):
        ret = "{}{}{}".format(ReST.monospace, "".join(elem.itertext()), ReST.monospace)
        return ret

    def open_moinpage_div(self, elem):
        """Only expected use of div is for a comment coming from rst_in:

        ..
          reST has unique block comment, similar moinwiki comments /* are inline */
        """
        if moin_page.class_ in elem.attrib:
            classes = elem.attrib[moin_page.class_].split()
            if "comment" in classes:
                comment = self.open_children(elem)
                if comment.startswith("\n"):
                    comment = comment[1:]
                comment = comment.replace("\n", "\n ")
                return f"\n..\n {comment}\n"
        # in case div has another use
        return self.open_children(elem)

    def open_moinpage_figure(self, elem):
        """
        Rework children to create an reST figure. Children are:
            * an image (.. image:: myimage)
            * a caption, figures have captions, images do not
            * optional text (may be several)
        """
        ret = self.open_children(elem).replace("image", "figure")
        ret = ret.split("\n")
        lines = []
        for r in ret:
            if r.startswith(("   ", "..")) or not r:
                lines.append(r)
            else:
                lines.append("   " + r)
        return "\n".join(lines)

    def open_moinpage_figcaption(self, elem):
        return f"\n   {self.open_children(elem)}\n"

    def open_moinpage_emphasis(self, elem):
        childrens_output = self.open_children(elem)
        return f"{ReST.emphasis}{childrens_output}{ReST.emphasis}"

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        text = "".join(elem.itertext())
        try:
            level = int(level)
        except ValueError:
            raise ElementException("page:outline-level needs to be an integer")
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        self.headings.append(text)
        if ReST.h_top[level] == " ":
            ret = f"\n{text}\n{ReST.h_bottom[level] * len(text)}\n"
        else:
            ret = f"\n{ReST.h_top[level] * len(text)}\n{text}\n{ReST.h_bottom[level] * len(text)}\n"
        return ret

    def open_xinclude_include(self, elem):
        """
        Return markup for a reST included item, something similar to:

        .. image:: png
           :height: 100
           :width: 200
           :alt: alternate text png
           :align: center
        """
        whitelist = {html.width: "width", html.height: "height", html.class_: "align", html.alt: "alt"}
        href = elem.attrib[xinclude.href]
        try:
            href = href.path
        except Exception:
            href = href.split("wiki.local:")[-1]
        ret = [f"\n.. image:: {href}"]
        for key, val in sorted(whitelist.items()):
            if key in elem.attrib:
                ret.append(f"   :{val}: {elem.attrib[key]}")
        if len(ret) == 1:
            # if there are no attributes, then (for now) we assume it is an include
            ret[0] = ret[0].replace("image", "include")
        return "\n".join(ret) + "\n"

    def open_moinpage_line_blk(self, elem):
        out = self.open_children(elem)
        if out.startswith("\n"):
            out = out[1:]
        return "| {}{}\n".format(" " * self.line_block_indent, out)

    def open_moinpage_line_block(self, elem):
        ret = []
        if self.line_block_indent < 0:
            ret.append("\n")
        self.line_block_indent += 4
        for child in elem:
            ret.append(self.open(child))
        self.line_block_indent -= 4
        return "".join(ret)

    def open_moinpage_line_break(self, elem):
        if self.status[-1] == "list":
            return ReST.linebreak + " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels))
        if self.last_closed == "p":
            return "\n\n"
        return ReST.linebreak

    def open_moinpage_list(self, elem):
        label_type = elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None)
        self.list_item_labels.append(ReST.list_type.get(label_type, " "))
        self.list_level += 1
        ret = ""
        self.status.append("list")
        self.last_closed = None
        ret += self.open_children(elem)
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        return ret

    def open_moinpage_list_item(self, elem):
        self.list_item_label = self.list_item_labels[-1] + " "
        return self.open_children(elem)

    def open_moinpage_list_item_label(self, elem):
        ret = ""
        if self.list_item_labels[-1] == "" or self.list_item_labels[-1] == " ":
            self.list_item_labels[-1] = " "
            self.list_item_label = self.list_item_labels[-1] + " "
            ret = " " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))
            if self.last_closed and self.last_closed != "list":
                ret = f"\n{ret}"
            return ret + self.open_children(elem)
        return self.open_children(elem)

    def open_moinpage_list_item_body(self, elem):
        ret = ""
        if not self.last_closed == "list_item":
            ret = "\n"
        ret += " " * (len("".join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1])) + self.list_item_label
        if self.list_item_labels[-1] in ["1.", "i.", "I.", "a.", "A."]:
            self.list_item_labels[-1] = "#."

        ret = self.define_references() + ret + self.open_children(elem)
        if self.last_closed == "text":
            return ret + "\n"
        return ret

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, "")
        if class_:
            self.status.append("list")
            if class_ == "footnote":
                self.footnotes.append(self.open_children(elem))
            self.status.pop()
        return " [#]_ "

    def open_moinpage_object(self, elem):
        # TODO: object parameters support
        href = elem.get(xlink.href, elem.get(xinclude.href, ""))
        if isinstance(href, Iri):
            href = str(href)
        href = href.split("?")
        args = ""
        if len(href) > 1:
            args = [s for s in re.findall(r"(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)", href[1]) if s[:3] != "do="]
        href = href[0]
        alt = elem.get(moin_page.alt, "")
        if not alt:
            ret = ""
        else:
            ret = f"|{alt}|"
        args_text = ""
        if args:
            args_text = "\n  {}".format(
                "\n  ".join(":{}: {}".format(arg.split("=")[0], arg.split("=")[1]) for arg in args)
            )
        self.objects.append(f".. {ret} image:: {href}{args_text}")
        return ret

    def open_moinpage_p(self, elem):
        ret = ""
        if self.status[-1] == "text":
            self.status.append("p")
            set = self.define_references()
            if self.last_closed == "text":
                ret = ReST.p * 2 + self.open_children(elem) + ReST.p + set
            elif self.last_closed:
                ret = ReST.p + self.open_children(elem) + ReST.p + set
            else:
                ret = self.open_children(elem) + ReST.p + set
        elif self.status[-1] == "table":
            self.status.append("p")
            if (
                self.last_closed
                and self.last_closed != "table_cell"
                and self.last_closed != "table_row"
                and self.last_closed != "table_header"
                and self.last_closed != "table_footer"
                and self.last_closed != "table_body"
                and self.last_closed != "line_break"
            ):
                # and self.last_closed != 'p':
                ret = ReST.linebreak + self.open_children(elem)
            elif self.last_closed == "p" or self.last_closed == "line_break":
                ret = self.open_children(elem)
            else:
                ret = self.open_children(elem)
        elif self.status[-1] == "list":
            self.status.append("p")
            if self.last_closed and self.last_closed == "list_item_label":
                ret = self.open_children(elem)
            elif (
                self.last_closed
                and self.last_closed != "list_item"
                and self.last_closed != "list_item_header"
                and self.last_closed != "list_item_footer"
                and self.last_closed != "p"
            ):
                ret = (
                    ReST.linebreak
                    + " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels))
                    + self.open_children(elem)
                )
            elif self.last_closed and self.last_closed == "p":
                # return ReST.p +\
                ret = (
                    "\n"
                    + " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels))
                    + self.open_children(elem)
                )
            else:
                ret = self.open_children(elem)
            if not self.delete_newlines:
                ret += "\n"
        else:
            self.status.append("p")
            ret = self.open_children(elem)
        self.status.pop()
        return ret

    def open_moinpage_page(self, elem):
        self.last_closed = None
        return self.open_children(elem)

    def open_moinpage_body(self, elem):
        return self.open_children(elem)

    def open_moinpage_part(self, elem, sep="\n"):
        type = elem.get(moin_page.content_type, "").split(";")
        if len(type) == 2:
            if type[0] == "x-moin/macro":
                if len(elem) and next(iter(elem)).tag.name == "arguments":
                    alt = "<<{}({})>>".format(type[1].split("=")[1], elem[0][0])
                else:
                    alt = "<<{}()>>".format(type[1].split("=")[1])
                return sep + f".. macro:: {alt}" + sep
            elif type[0] == "x-moin/format":
                elem_it = iter(elem)
                ret = "\n\n.. parser:{}".format(type[1].split("=")[1])
                if len(elem) and next(elem_it).tag.name == "arguments":
                    args = []
                    for arg in next(iter(elem)):
                        if arg.tag.name == "argument":
                            args.append('{}="{}"'.format(arg.get(moin_page.name, ""), " ".join(arg.itertext())))
                    ret = "{} {}".format(ret, " ".join(args))
                    elem = next(elem_it)
                ret = "{}\n  {}".format(ret, " ".join(elem.itertext()))
                return ret
        return elem.get(moin_page.alt, "") + "\n"

    def open_moinpage_inline_part(self, elem, sep=""):
        return self.open_moinpage_part(elem)

    def open_moinpage_separator(self, elem):
        return "\n\n" + ReST.separator + "\n\n"

    def open_moinpage_span(self, elem):
        baseline_shift = elem.get(moin_page.baseline_shift, "")
        if baseline_shift == "super":
            return "\\ :sup:`{}`\\ ".format("".join(elem.itertext()))
        if baseline_shift == "sub":
            return "\\ :sub:`{}`\\ ".format("".join(elem.itertext()))
        id = elem.get(moin_page.id, "")
        if id:
            self.headings.append(id)
            return f"\n.. _{id}:\n"
        return self.open_children(elem)

    def open_moinpage_strong(self, elem):
        return ReST.strong + self.open_children(elem) + ReST.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get("class", "")
        self.table_tablestyle = elem.attrib.get("style", "")
        self.table_rowsstyle = ""
        self.table_rowsclass = ""
        self.status.append("table")
        self.last_closed = None
        self.table = []
        self.tablec = Table()
        self.open_children(elem)
        self.status.pop()
        table = repr(self.tablec)
        if self.status[-1] == "list":
            table = re.sub(
                r"\n(.)",
                lambda m: "\n{}{}".format(
                    " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)
                ),
                "\n" + table,
            )
            return table + ReST.p
        return "\n" + table + ReST.linebreak

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.tablec.rowclass = "table-header"
        return self.open_children(elem)

    def open_moinpage_table_body(self, elem):
        self.tablec.rowclass = "table-body"
        return self.open_children(elem)

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get("class", "")
        self.table_rowclass = " ".join([s for s in [self.table_rowsclass, self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get("style", "")
        self.table_rowstyle = " ".join([s for s in [self.table_rowsstyle, self.table_rowstyle] if s])
        self.table.append([])
        self.tablec.add_row()
        ret = self.open_children(elem)
        self.table_rowstyle = ""
        self.table_rowclass = ""
        self.tablec.end_row()
        return ret

    def open_moinpage_table_cell(self, elem):
        number_cols_spanned = int(elem.get(moin_page.number_cols_spanned, 1))
        number_rows_spanned = int(elem.get(moin_page.number_rows_spanned, 1))
        self.table[-1].append((number_cols_spanned, number_rows_spanned, [self.open_children(elem)]))
        cell = self.table[-1][-1]
        self.tablec.add_cell(cell[0], cell[1], Cell("".join(cell[2])))
        return ""

    def open_moinpage_table_of_content(self, elem):
        depth = elem.get(moin_page.outline_level, "")
        ret = "\n\n.. contents::"
        if depth:
            ret += f"\n   :depth: {depth}"
        return ret + "\n\n"

    def define_references(self):
        """
        Adds definitions of found links and objects to the converter output.
        """
        ret = ""
        self.all_used_references.extend(self.used_references)
        definitions = [
            " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)) + f".. _{t}: {h}"
            for t, h in self.used_references
            if t not in self.headings
        ]
        definitions.extend(
            " " * (len("".join(self.list_item_labels)) + len(self.list_item_labels)) + link for link in self.objects
        )
        # convert ".. _example: wiki.local:#example" to ".. _example:"
        definitions = [x.split(" wiki.local")[0] for x in definitions]
        definition_block = "\n\n".join(definitions)

        if definitions:
            if self.last_closed == "list_item_label":
                ret += f"\n{definition_block}\n\n"
            else:
                ret += f"\n\n{definition_block}\n\n"

        self.used_references = []
        self.objects = []
        self.anonymous_reference = None
        return ret


default_registry.register(Converter.factory, type_moin_document, Type("text/x-rst"))
default_registry.register(Converter.factory, type_moin_document, Type("x-moin/format;name=rst"))
