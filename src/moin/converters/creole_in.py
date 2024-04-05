# Copyright: 2007 MoinMoin:RadomirDopieralski (creole 0.5 implementation)
# Copyright: 2007 MoinMoin:ThomasWaldmann (updates)
# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Creole input converter

See http://wikicreole.org/ for latest specs.

Notes:

- No markup allowed in headings.
  Creole 1.0 does not require us to support this.
- No markup allowed in table headings.
  Creole 1.0 does not require us to support this.
- No (non-bracketed) generic url recognition: this is "mission impossible"
  except if you want to risk lots of false positives. Only known protocols
  are recognized.
- We do not allow ":" before "//" italic markup to avoid urls with
  unrecognized schemes (like wtf://server/path) triggering italic rendering
  for the rest of the paragraph.
"""

import re

from moin.constants.misc import URI_SCHEMES
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.utils.interwiki import is_known_wiki
from moin.utils.mime import Type, type_moin_document, type_moin_creole

from . import default_registry
from ._args_wiki import parse as parse_arguments
from ._wiki_macro import ConverterMacro
from ._util import decode_data, normalize_split_text, _Iter, _Stack


class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        lines = normalize_split_text(text)
        iter_content = _Iter(lines)

        body = self.parse_block(iter_content, arguments)
        root = moin_page.page(children=[body])

        return root

    block_head = r"""
        (?P<head>
            ^
            \s*
            (?P<head_head> =+)
            \s*
            (?P<head_text> .*?)
            \s*
            =*
            \s*
            $
        )
    """

    def block_head_repl(self, _iter_content, stack, head, head_head, head_text):
        stack.clear()

        attrib = {moin_page.outline_level: str(len(head_head))}
        element = moin_page.h(attrib=attrib, children=(head_text,))
        stack.top_append(element)

    # Matches an empty (only whitespaces) line.
    block_line = r"(?P<line> ^ \s* $ )"

    def block_line_repl(self, _iter_content, stack, line):
        stack.clear()

    # Matches the beginning of a list. All lines within a list are handled by
    # list_*.
    block_list = r"""
        (?P<list>
            ^
            \s*
            [*\#][^*\#]
            .*
            $
        )
    """

    def block_list_repl(self, iter_content, stack, list):
        iter_content.push(list)

        for line in iter_content:
            match = self.list_re.match(line)
            self._apply(match, "list", iter_content, stack)

            if match.group("end") is not None:
                # Allow the mainloop to take care of the line after a list.
                iter_content.push(line)
                break

    block_macro = r"""
        ^
        \s*
        (?P<macro>
            <<
            (?P<macro_name> \w+)
            (
                \(
                (?!.*>>.*>>)
                (?P<macro_args> .*?)
                \)
            )?
            \s*
            >>
        )
        \s*
        $
    """

    def block_macro_repl(self, _iter_content, stack, macro, macro_name, macro_args=None):
        """Handles macros using the placeholder syntax."""
        stack.clear()
        elem = self.macro(macro_name, macro_args, macro, True)
        stack.top_append_ifnotempty(elem)

    # Matches the beginning of a nowiki block
    block_nowiki = r"""
        (?P<nowiki>
            ^{{{
            \s*
            $
        )
    """

    # Matches the interpreter line of a nowiki block
    nowiki_interpret = r"""
        ^
        \#!
        \s*
        (?P<nowiki_name> [\w/]+)?
        \s*
        (:?
            \(
            (?P<nowiki_args> .*?)
            \)
        )?
        \s*
        $
    """

    # Matches the possibly escaped end of a nowiki block
    nowiki_end = r"""
        ^ (?P<escape> ~ )? (?P<rest> }}} \s* ) $
    """

    def block_nowiki_lines(self, iter_content):
        """Unescaping generator for the lines in a nowiki block"""

        for line in iter_content:
            match = self.nowiki_end_re.match(line)
            if match:
                if not match.group("escape"):
                    return
                line = match.group("rest")
            yield line

    def block_nowiki_repl(self, iter_content, stack, nowiki):
        """Handles a complete nowiki block"""

        stack.clear()

        try:
            firstline = next(iter_content)
        except StopIteration:
            stack.push(moin_page.blockcode())
            return

        # Stop directly if we got an end marker in the first line
        match = self.nowiki_end_re.match(firstline)
        if match and not match.group("escape"):
            stack.push(moin_page.blockcode())
            return

        lines = _Iter(self.block_nowiki_lines(iter_content), startno=iter_content.lineno)

        match = self.nowiki_interpret_re.match(firstline)

        if match:
            name = match.group("nowiki_name")
            args = match.group("nowiki_args")
            if args:
                args = parse_arguments(args)

            # Parse it directly if the type is ourself
            if not name or name == "creole":
                body = self.parse_block(lines, args)
                elem = moin_page.page(children=(body,))
                stack.top_append(elem)

            else:
                stack.top_append(self.parser(name, args, lines))

        else:
            elem = moin_page.blockcode(children=(firstline,))
            stack.top_append(elem)

            for line in lines:
                elem.append("\n")
                elem.append(line)

    block_separator = r"(?P<separator> ^ \s* ---- \s* $ )"

    def block_separator_repl(self, _iter_content, stack, separator, hr_class="moin-hr3"):
        stack.clear()
        stack.top_append(moin_page.separator(attrib={moin_page.class_: hr_class}))

    block_table = r"""
        (?P<table>
            ^ \s* \| .* $
        )
    """

    def block_table_repl(self, iter_content, stack, table):
        stack.clear()

        element = moin_page.table()
        stack.push(element)
        element = moin_page.table_body()
        stack.push(element)

        self.block_table_row(table, stack)

        for line in iter_content:
            match = self.table_re.match(line)
            if not match:
                # Allow the mainloop to take care of the line after a list.
                iter_content.push(line)
                break

            self.block_table_row(match.group("table"), stack)

        stack.clear()

    def block_table_row(self, content, stack):
        element = moin_page.table_row()
        stack.push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, "tablerow", stack)

        stack.pop()

    block_text = r"(?P<text> .+ )"

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check("table", "table-body", "list"):
            stack.clear()

        if stack.top_check("body"):
            element = moin_page.p()
            stack.push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            stack.top_append("\n")
        self.parse_inline(text, stack)

    inline_emph = r"(?P<emph> (?<!:)// )"
    # there must be no : in front of the // avoids italic rendering in urls
    # with unknown protocols

    def inline_emph_repl(self, stack, emph):
        if not stack.top_check("emphasis"):
            stack.push(moin_page.emphasis())
        else:
            stack.pop_name("emphasis")

    inline_insert = r"(?P<insert> (?<!:)__ )"

    def inline_insert_repl(self, stack, insert):
        # creole docs suggest u, but ins is consistent with moinwiki and html5 ins/u docs
        if not stack.top_check("ins"):
            stack.push(moin_page.ins())
        else:
            stack.pop_name("ins")

    inline_strong = r"(?P<strong> \*\* )"

    def inline_strong_repl(self, stack, strong):
        if not stack.top_check("strong"):
            stack.push(moin_page.strong())
        else:
            stack.pop_name("strong")

    inline_linebreak = r"(?P<linebreak> \\\\ )"

    def inline_linebreak_repl(self, stack, linebreak):
        element = moin_page.line_break()
        stack.top_append(element)

    inline_escape = r"(?P<escape> ~ (?P<escaped_char>\S) )"

    def inline_escape_repl(self, stack, escape, escaped_char):
        stack.top_append(escaped_char)

    inline_link = r"""
        (?P<link>
            \[\[
            \s*
            (
                (?P<link_url>
                    (%(uri_schemes)s):
                    [^|]+?
                )
                |
                (
                    (?P<link_interwiki_site>[A-Z][a-zA-Z]+)
                    :
                    (?P<link_interwiki_item>[^|]+) # accept any item name; will verify link_interwiki_site below
                )
                |
                (?P<link_item> [^|]+? )
            )
            \s*
            ([|] \s* (?P<link_text>.+?) \s*)?
            \]\]
        )
    """ % dict(
        uri_schemes="|".join(URI_SCHEMES)
    )

    def inline_link_repl(
        self,
        stack,
        link,
        link_url=None,
        link_item=None,
        link_text=None,
        link_interwiki_site=None,
        link_interwiki_item=None,
    ):
        """Handle all kinds of links."""
        if link_interwiki_site:
            if is_known_wiki(link_interwiki_site):
                link = Iri(scheme="wiki", authority=link_interwiki_site, path="/" + link_interwiki_item)
                element = moin_page.a(attrib={xlink.href: link})
                stack.push(element)
                if link_text:
                    self.parse_inline(link_text, stack, self.inlinedesc_re)
                else:
                    stack.top_append(link_interwiki_item)
                stack.pop()
                return
            else:
                # assume local language uses ":" inside of words, set link_item and continue
                link_item = f"{link_interwiki_site}:{link_interwiki_item}"
        if link_item is not None:
            att = "attachment:"  # moin 1.9 needed this for an attached file
            if link_item.startswith(att):
                link_item = "/" + link_item[len(att) :]  # now we have a subitem
            # we have Anchor macro, so we support anchor links despite lack of docs in Creole spec
            if "#" in link_item:
                path, fragment = link_item.rsplit("#", 1)
            else:
                path, fragment = link_item, None
            target = Iri(scheme="wiki.local", path=path, fragment=fragment)
            text = link_item
        else:
            target = Iri(link_url)
            text = link_url
        element = moin_page.a(attrib={xlink.href: target})
        stack.push(element)
        if link_text:
            self.parse_inline(link_text, stack, self.inlinedesc_re)
        else:
            stack.top_append(text)
        stack.pop()

    inline_macro = r"""
        (?P<macro>
            <<
            (?P<macro_name> \w+)
            (?:
                \(
                (?P<macro_args> .*?)
                \)
            )?
            \s*
            >>
        )
    """

    def inline_macro_repl(self, stack, macro, macro_name, macro_args=None):
        """Handles macros using the placeholder syntax."""
        elem = self.macro(macro_name, macro_args, macro)
        stack.top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
        )
    """

    def inline_nowiki_repl(self, stack, nowiki, nowiki_text):
        stack.top_append(moin_page.code(children=(nowiki_text,)))

    inline_object = r"""
        (?P<object>
            {{
            \s*
            (
                (?P<object_url>
                    [a-zA-Z0-9+.-]+
                    ://
                    [^|]+?
                )
                |
                (?P<object_page> [^|]+? )
            )
            \s*
            ([|] \s* (?P<object_text>.+?) \s*)?
            }}
        )
    """

    def inline_object_repl(self, stack, object, object_page=None, object_url=None, object_text=None):
        """Handles objects included in the page."""
        attrib = {}
        if object_text:
            attrib[html.alt] = object_text
        if object_page is not None:
            att = "attachment:"  # moin 1.9 needed this for an attached file
            if object_page.startswith(att):
                object_page = "/" + object_page[len(att) :]  # now we have a subitem
            target = Iri(scheme="wiki.local", path=object_page)
            attrib[xinclude.href] = target
            element = xinclude.include(attrib=attrib)
        else:
            attrib[xlink.href] = object_url
            element = moin_page.object(
                attrib=attrib, children=("Your Browser does not support HTML5 audio/video element.",)
            )
        stack.top_append(element)

    inline_url = r"""
        (?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<escaped_url>~)?
            (?P<url_target>
                (%(uri_schemes)s)
                :
                \S+?
            )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )
    """ % dict(
        uri_schemes="|".join(URI_SCHEMES)
    )

    def inline_url_repl(self, stack, url, url_target, escaped_url=None):
        """Handle raw urls in text."""

        if not escaped_url:
            # this url is NOT escaped
            attrib = {xlink.href: url_target}
            element = moin_page.a(attrib=attrib, children=(url_target,))
            stack.top_append(element)
        else:
            # this url is escaped, we render it as text
            stack.top_append(url_target)

    # Matches a line which will end a list
    list_end = r"""
        (?P<end>
            ^
            (
                # End the list on blank line,
                $
                |
                # heading,
                =
                |
                # table,
                \|
                |
                # and nowiki block
                {{{
            )
        )
    """

    def list_end_repl(self, _iter_content, stack, end):
        stack.clear()

    # Matches a single list item
    list_item = r"""
        (?P<item>
            ^
            \s*
            (?P<item_head> [\#*]+)
            \s*
            (?P<item_text> .*?)
            $
        )
    """

    def list_item_repl(self, _iter_content, stack, item, item_head, item_text):
        list_level = len(item_head)
        list_type = item_head[-1]

        # Try to locate the list element which matches the requested level and
        # type.
        while True:
            cur = stack.top()
            if cur.tag.name == "body":
                break
            if cur.tag.name == "list-item-body":
                if list_level > cur.list_level:
                    break
            if cur.tag.name == "list":
                if list_level >= cur.list_level and list_type == cur.list_type:
                    break
            stack.pop()

        if cur.tag.name != "list":
            generate = list_type == "#" and "ordered" or "unordered"
            attrib = {moin_page.item_label_generate: generate}
            element = moin_page.list(attrib=attrib)
            element.list_level, element.list_type = list_level, list_type
            stack.push(element)

        element = moin_page.list_item()
        element_body = moin_page.list_item_body()
        element_body.list_level, element_body.list_type = list_level, list_type

        stack.push(element)
        stack.push(element_body)

        self.parse_inline(item_text, stack)

    list_text = block_text

    list_text_repl = block_text_repl

    table = block_table

    tablerow = r"""
        (?P<cell>
            \|
            \s*
            (?P<cell_head> [=] )?
            # a table cells may contain links (which may contain |) or characters that are not |
            (?P<cell_text> (\[\[.*?\]\]|[^|])+ )
            \s*
        )
    """

    def tablerow_cell_repl(self, stack, cell, cell_text, cell_head=None):
        """
        Creole has feature that allows table headings to be either row based or column based.

        We avoid use of HTML5 row based thead tag and apply CSS styling to any cell marked as a heading.
        """
        attrib = {}
        if cell_head:
            attrib[moin_page.class_] = "moin-thead"
        element = moin_page.table_cell(attrib=attrib)
        stack.push(element)
        self.parse_inline(cell_text.strip(), stack)
        stack.pop_name("table-cell")

    # Block elements
    block = (block_line, block_head, block_separator, block_macro, block_nowiki, block_list, block_table, block_text)
    block_re = re.compile("|".join(block), re.X | re.U)

    # Inline elements
    inline = (
        inline_url,
        inline_escape,
        inline_link,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_strong,
        inline_emph,
        inline_insert,
        inline_linebreak,
    )
    inline_re = re.compile("|".join(inline), re.X | re.U)

    inlinedesc = (inline_macro, inline_nowiki, inline_emph, inline_strong, inline_object)
    inlinedesc_re = re.compile("|".join(inlinedesc), re.X | re.U)

    # Link description
    link_desc = (inline_object, inline_linebreak)
    link_desc_re = re.compile("|".join(link_desc), re.X | re.U)

    # List items
    list = (list_end, list_item, list_text)
    list_re = re.compile("|".join(list), re.X | re.U)

    # Nowiki interpreter
    nowiki_interpret_re = re.compile(nowiki_interpret, re.X)

    # Nowiki end
    nowiki_end_re = re.compile(nowiki_end, re.X)

    # Table
    table_re = re.compile(table, re.X | re.U)

    # Table row
    tablerow_re = re.compile(tablerow, re.X | re.U)

    def _apply(self, match, prefix, *args):
        """
        Call the _repl method for the last matched group with the given prefix.
        """
        data = {k: v for k, v in match.groupdict().items() if v is not None}
        getattr(self, f"{prefix}_{match.lastgroup}_repl")(*args, **data)

    def parse_block(self, iter_content, arguments):
        attrib = {}
        if arguments:
            for key, value in arguments.keyword.items():
                if key in ("style",):
                    attrib[moin_page(key)] = value

        body = moin_page.body(attrib=attrib)

        stack = _Stack(body, iter_content=iter_content)

        # Please note that the iterator can be modified by other functions
        for line in iter_content:
            match = self.block_re.match(line)
            self._apply(match, "block", iter_content, stack)

        return body

    def parse_inline(self, text, stack, inline_re=inline_re):
        """Recognize inline elements within the given text"""

        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            stack.top_append_ifnotempty(text[pos : match.start()])
            pos = match.end()

            self._apply(match, "inline", stack)

        # Handle trailing text
        stack.top_append_ifnotempty(text[pos:])

    def macro_text(self, text):
        """
        Return an ET tree branch representing the markup present in the input text. Used for FootNotes, etc.
        """
        p = moin_page.p()
        iter_content = _Iter(text)
        stack = _Stack(p, iter_content=iter_content)
        self.parse_inline(text, stack, self.inline_re)
        return p


default_registry.register(Converter.factory, type_moin_creole, type_moin_document)
default_registry.register(Converter.factory, Type("x-moin/format;name=creole"), type_moin_document)
