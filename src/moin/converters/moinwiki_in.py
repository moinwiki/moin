# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Moin Wiki input converter
"""

import re

from flask import request
from urllib.parse import urlencode

from moin.constants.contenttypes import CHARSET
from moin.constants.misc import URI_SCHEMES
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.utils.interwiki import is_known_wiki
from moin.utils.mime import Type, type_moin_document, type_moin_wiki
from moin.i18n import _

from ._args import Arguments
from ._args_wiki import parse as parse_arguments, object_re
from ._wiki_macro import ConverterMacro
from ._util import decode_data, normalize_split_text, _Iter, _Stack
from . import default_registry

from moin import log

logging = log.getLogger(__name__)


class _TableArguments:
    rules = r"""
    (?:
        - (?P<number_columns_spanned> \d+)
        |
        \| (?P<number_rows_spanned> \d+)
        |
        (?P<width_percent> \d+\%)
        |
        v (?P<vertical_align_bottom> )
        |
        \^ (?P<vertical_align_top> )
        |
        \( (?P<text_align_left> )
        |
        : (?P<text_align_center> )
        |
        \) (?P<text_align_right> )
        |
        (?P<arg>
            (?:
                (?P<key> [-\w]+)
                =
            )?
            (?:
                (?P<value_u> [-\w]+)
                |
                "
                (?P<value_q1> .*?)
                (?<!\\)"
                |
                '
                (?P<value_q2> .*?)
                (?<!\\)'
            )
        )
        |
        \# (?P<hex_color_code> ([A-Fa-f0-9]){3}(([A-Fa-f0-9]){3})?)
        |
        (?P<syntax_error> \S+?)
    )
    """
    _re = re.compile(rules, re.X)

    map_keys = {"colspan": "number-columns-spanned", "rowspan": "number-rows-spanned"}

    def arg_repl(self, args, arg, key=None, value_u=None, value_q1=None, value_q2=None):
        key = self.map_keys.get(key, key)
        value = (value_u or value_q1 or value_q2).encode("ascii", errors="backslashreplace").decode("unicode-escape")
        if key:
            args.keyword[key] = value
        else:
            args.positional.append(value)

    def number_columns_spanned_repl(self, args, number_columns_spanned):
        args.keyword["number-columns-spanned"] = int(number_columns_spanned)

    def number_rows_spanned_repl(self, args, number_rows_spanned):
        args.keyword["number-rows-spanned"] = int(number_rows_spanned)

    def add_attr_to_style(self, args, attr):
        args.keyword["style"] = args.keyword.get("style", "") + attr + " "

    def hex_color_code_repl(self, args, hex_color_code):
        self.add_attr_to_style(args, f"background-color: #{hex_color_code};")

    def vertical_align_top_repl(self, args, vertical_align_top):
        self.add_attr_to_style(args, "vertical-align: top;")

    def vertical_align_bottom_repl(self, args, vertical_align_bottom):
        self.add_attr_to_style(args, "vertical-align: bottom;")

    def text_align_left_repl(self, args, text_align_left):
        self.add_attr_to_style(args, "text-align: left;")

    def text_align_center_repl(self, args, text_align_center):
        self.add_attr_to_style(args, "text-align: center;")

    def text_align_right_repl(self, args, text_align_right):
        self.add_attr_to_style(args, "text-align: right;")

    def width_percent_repl(self, args, width_percent):
        self.add_attr_to_style(args, f"width: {width_percent};")

    def syntax_error_repl(self, args, syntax_error):
        args.keyword["error"] = syntax_error

    def __call__(self, input):
        args = Arguments()

        for match in self._re.finditer(input):
            data = {str(k): v for k, v in match.groupdict().items() if v is not None}
            getattr(self, f"{match.lastgroup}_repl")(args, **data)

        return args


class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        lines = normalize_split_text(text)
        iter_content = _Iter(lines)

        body = self.parse_block(iter_content, arguments)
        root = moin_page.page(children=(body,))

        return root

    block_comment = r"""
        (?P<comment>
            ^ \#\#.*$
        )
    """

    def block_comment_repl(self, _iter_content, stack, comment):
        # A comment also ends anything
        if not stack.top_check("block-comment"):
            stack.clear()
            elem = moin_page.block_comment(children=(comment,))
            stack.push(elem)
        else:
            stack.top_append(comment)

    block_head = r"""
        (?P<head>
            ^
            \s*
            (?P<head_head> =+ )
            \s+  # for better moin 1.x compatibility, we require 1+ blank(s)
            (?P<head_text> .*? )
            \s+  # for better moin 1.x compatibility, ...
            (?P=head_head)
            \s*
            $
        )
    """

    def block_head_repl(self, _iter_content, stack, head, head_head, head_text):
        stack.clear()

        attrib = {moin_page.outline_level: str(len(head_head))}
        element = moin_page.h(attrib=attrib)
        stack.push(element)
        # heading text may have wiki markup, including links
        self.parse_inline(head_text, stack, self.inline_re)
        stack.pop()

    block_line = r"(?P<line> ^ \s* $ )"
    # empty line that separates paragraphs

    def block_line_repl(self, _iter_content, stack, line):
        stack.clear()

    block_macro = r"""
        ^
        \s*
        (?P<macro>
            <<
            (?P<macro_name> \w+ )
            (
                \(
                (?!.*>>.*>>)
                (?P<macro_args> .*? )
                \)
            )?
            \s*
            >>
        )
        \s*
        $
    """

    def block_macro_repl(self, _iter_content, stack, macro, macro_name, macro_args=""):
        """Handles macros using the placeholder syntax.

        Arguments are passed as a single positional parameter, each macro must parse as required.
        """

        stack.clear()
        elem = self.macro(macro_name, macro_args, macro, True)
        stack.top_append_ifnotempty(elem)

    block_nowiki = r"""
        (?P<nowiki>
            ^
            \s*
            (?P<nowiki_marker> \{{3,} )
            \s*                               # spaces not defined here, but accepted with no error messages
            (?P<nowiki_interpret>
                \#!
                \s*                           # spaces not allowed here, error message generated
                (?P<nowiki_name> [\w/.-]+ )?  # wiki | csv | highlight | creole (same result as highlight creole)
                \s*
                (:?
                    \(
                    (?P<nowiki_args> .*? )    # (style="color: red;")
                    \)
                    |
                    (?P<optional_args> .+ )   # csv , -2 -3 | highlight python numbers=on start=222
                )?
            )?
            \s*
            $
        )
    """
    # Matches the beginning of a nowiki block

    nowiki_end = r"""
        ^
        \s*
        (?P<marker> }{3,} )
        \s*
        $
    """
    # Matches the possibly escaped end of a nowiki block

    def block_nowiki_lines(self, iter_content, marker_len):
        """Unescaping generator for the lines in a nowiki block"""

        for line in iter_content:
            match = self.nowiki_end_re.match(line)
            if match:
                marker = match.group("marker")
                if len(marker) == marker_len:
                    return
            yield line

    def block_nowiki_repl(
        self,
        iter_content,
        stack,
        nowiki,
        nowiki_marker,
        nowiki_interpret="",
        nowiki_name=None,
        nowiki_args=None,
        optional_args=None,
    ):
        stack.clear()
        lines = _Iter(self.block_nowiki_lines(iter_content, len(nowiki_marker)), startno=iter_content.lineno)
        content = "\n".join(lines)
        # the arguments for wiki, csv, and highlight are diverse, one parser does not fit all
        # we push everything after {{{ to DOM; nowiki.py can insert error messages or
        # moinwiki_out can recreate exact input
        all_nowiki_args = moin_page.nowiki_args(children=(nowiki_interpret,))
        # we avoid adjacent text siblings because serializer within tests merges them
        elem = moin_page.nowiki(children=(str(len(nowiki_marker)), all_nowiki_args, content))
        stack.top_append(elem)

    block_separator = r"(?P<separator> ^ \s* -{4,} \s* $ )"

    def block_separator_repl(self, _iter_content, stack, separator, hr_class="moin-hr{0}"):
        stack.clear()
        hr_height = min((len(separator) - 3), 6)
        hr_height = max(hr_height, 1)
        attrib = {moin_page("class"): hr_class.format(hr_height)}
        elem = moin_page.separator(attrib=attrib)
        stack.top_append(elem)

    block_table = r"""
        ^
        \s*
        (?P<table>
            \|\|
            .*
        )
        \|\|
        \s*
        $
    """

    header_footer_separator = r"""
        ^
        \s*
        (?P<table_sep>
            ===+
        )
        \s*
        $
    """

    def block_table_repl(self, iter_content, stack, table):
        stack.clear()

        element = moin_page.table(attrib={moin_page("class"): "moin-wiki-table"})
        stack.push(element)
        stack.push(moin_page.table_body())

        self.block_table_row(table, stack, element)

        for line in iter_content:
            match = self.table_re.match(line)
            if not match:
                match = self.header_footer_re.match(line)
                if match:
                    # this is a header/body/footer separator: create multiple table_body's,
                    # html_out will convert to thead, tbody or tfoot
                    stack.pop()
                    stack.push(moin_page.table_body())
                    continue
                else:
                    # Allow the mainloop to take care of the line after table end.
                    iter_content.push(line)
                    break
            self.block_table_row(match.group("table"), stack, element)

    def block_table_row(self, content, stack, table):
        element = moin_page.table_row()
        stack.push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, "tablerow", stack, table, element)

        stack.pop()

    block_text = r"(?P<text> .+ )"

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check("table", "table-body", "list", "block-comment"):
            stack.clear()
        if stack.top_check("body"):
            element = moin_page.p()
            stack.push(element)
        elif stack.top_check("p") or len(stack.top()):
            # we are in a paragraph or multi-line list item, don't loose the whitespace
            stack.top_append("\n")
        self.parse_inline(text, stack, self.inline_re)

    indent = r"""
        ^
        (?P<indent> \s* )
        (?P<list_begin>
            (?P<list_definition>
                (?P<list_definition_text> .*? )
                ::
            )
            \s*
            |
            (?P<list_numbers> [0-9]+\. (\#(?P<list_start_number>[0-9]+))?)
            \s+
            |
            (?P<list_alpha> [aA]\. (\#(?P<list_start_alpha>[0-9]+))?)
            \s+
            |
            (?P<list_roman> [iI]\. (\#(?P<list_start_roman>[0-9]+))?)
            \s+
            |
            (?P<list_bullet> \* )
            \s*
            |
            (?P<list_none> \. )
            \s*
        )?
        (?P<text> .*? )
        $
    """

    def indent_iter(self, iter_content, line, level):
        yield line

        while True:
            try:
                line = next(iter_content)
            except StopIteration:
                return

            match = self.indent_re.match(line)

            new_level = 0
            if match.group("indent"):
                new_level = len(match.group("indent"))

            if match.group("list_begin") or level != new_level:
                iter_content.push(line)
                return

            yield match.group("text")

    def indent_repl(
        self,
        iter_content,
        stack,
        line,
        indent,
        text,
        list_begin=None,
        list_definition=None,
        list_definition_text=None,
        list_numbers=None,
        list_alpha=None,
        list_roman=None,
        list_bullet=None,
        list_start_number=None,
        list_start_roman=None,
        list_start_alpha=None,
        list_none=None,
    ):

        level = len(indent)

        # default to blockquote / indented text / bulletless list
        list_type = "unordered", "no-bullet"

        if list_begin:
            if list_definition:
                list_type = "definition", None
            elif list_numbers:
                list_type = "ordered", None
            elif list_alpha and list_alpha[:2] == "A.":
                list_type = "ordered", "upper-alpha"
            elif list_alpha:
                list_type = "ordered", "lower-alpha"
            elif list_roman and list_roman[:2] == "I.":
                list_type = "ordered", "upper-roman"
            elif list_roman:
                list_type = "ordered", "lower-roman"
            elif list_bullet == "*":
                list_type = "unordered", None

        element_use = None
        while len(stack) > 1:
            cur = stack.top()
            if cur.tag.name == "list-item-body":
                if level > cur.level:
                    element_use = cur
                    break
            if cur.tag.name == "list":
                if level >= cur.level and list_type == cur.list_type:
                    element_use = cur
                    break
            stack.pop()

        if not element_use:
            element_use = stack.top()

        if indent:
            if element_use.tag.name != "list":
                attrib = {}
                if not list_definition:
                    attrib[moin_page.item_label_generate] = list_type[0]
                if list_type[1]:
                    attrib[moin_page.list_style_type] = list_type[1]
                if list_start_number or list_start_alpha or list_start_roman:
                    attrib[moin_page.list_start] = list_start_number or list_start_alpha or list_start_roman
                element = moin_page.list(attrib=attrib)
                element.level, element.list_type = level, list_type
                stack.push(element)

            stack.push(moin_page.list_item())

            if list_definition_text:
                element_label = moin_page.list_item_label()
                stack.top_append(element_label)
                new_stack = _Stack(element_label, iter_content=iter_content)

                self.parse_inline(list_definition_text, new_stack, self.inline_re)
            if not list_definition_text or text:
                # if text == true, then we have object:: definition, not object::\n ::definition
                element_body = moin_page.list_item_body()
                element_body.level, element_body.type = level, type

                stack.push(element_body)
                new_stack = _Stack(element_body, iter_content=iter_content)
        else:
            new_stack = stack

        iter = _Iter(self.indent_iter(iter_content, text, level), startno=iter_content.lineno)
        for line in iter:
            match = self.block_re.match(line)
            it = iter
            # XXX: Hack to allow nowiki to ignore the list indentation
            if match.lastgroup == "nowiki":
                it = iter_content
            self._apply(match, "block", it, new_stack)

    inline_comment = r"""
        (?P<comment>
            (?P<comment_begin>
                (^|(?<=\s))
                /\*
                \s+
            )
            |
            (?P<comment_end>
                \s+
                \*/
                ((?=\s)|$)
            )
        )
    """

    def inline_comment_repl(self, stack, comment, comment_begin=None, comment_end=None):
        if comment_begin:
            attrib = {moin_page("class"): "comment"}
            elem = moin_page.span(attrib=attrib)
            stack.push(elem)
        else:
            stack.pop()

    inline_emphstrong = r"""
        (?P<emphstrong>
            '{2,6}
            (?=
                [^']+
                (?P<emphstrong_follow>
                    '{2,3}
                    (?!')
                )
            )?
        )
    """

    def inline_emphstrong_repl(self, stack, emphstrong, emphstrong_follow=""):
        if len(emphstrong) == 5:
            if stack.top_check("emphasis"):
                stack.pop()
                if stack.top_check("strong"):
                    stack.pop()
                else:
                    stack.push(moin_page.strong())
            elif stack.top_check("strong"):
                stack.pop()
                if stack.top_check("emphasis"):
                    stack.pop()
                else:
                    stack.push(moin_page.emphasis())
            else:
                if len(emphstrong_follow) == 3:
                    stack.push(moin_page.emphasis())
                    stack.push(moin_page.strong())
                else:
                    stack.push(moin_page.strong())
                    stack.push(moin_page.emphasis())
        elif len(emphstrong) == 3:
            if stack.top_check("strong"):
                stack.pop()
            else:
                stack.push(moin_page.strong())
        elif len(emphstrong) == 2:
            if stack.top_check("emphasis"):
                stack.pop()
            else:
                stack.push(moin_page.emphasis())

    inline_entity = r"""
        (?P<entity>
            &
            (?:
               # symbolic entity, like &uuml;
               [0-9a-zA-Z]{2,6}
               |
               # numeric decimal entities, like &#42;
               \#\d{1,5}
               |
               # numeric hexadecimal entities, like &#x42;
               \#x[0-9a-fA-F]{1,6}
           )
           ;
       )
    """

    def inline_entity_repl(self, stack, entity):
        if entity[1] == "#":
            if entity[2] == "x":
                c = int(entity[3:-1], 16)
            else:
                c = int(entity[2:-1], 10)
            c = chr(c)
        else:
            from html.entities import name2codepoint

            c = chr(name2codepoint.get(entity[1:-1], 0xFFFE))
        stack.top_append(c)

    inline_size = r"""
        (?P<size>
           (?P<size_begin>
              ~[-+]
           )
           |
           (?P<size_end>
              [-+]~
           )
        )
    """

    def inline_size_repl(self, stack, size, size_begin=None, size_end=None):
        if size_begin:
            size = "120%" if size[1] == "+" else "85%"
            attrib = {moin_page.font_size: size}
            elem = moin_page.span(attrib=attrib)
            stack.push(elem)
        else:
            stack.pop()

    inline_strike = r"""
        (?P<strike>
           (?P<strike_begin>)
           --\(
           |
           \)--
        )
    """

    def inline_strike_repl(self, stack, strike, strike_begin=None):
        if strike_begin is not None:
            stack.push(moin_page.del_())
        else:
            stack.pop()

    inline_subscript = r"""
        (?P<subscript>
            ,,
            (?P<subscript_text> .*? )
            ,,
        )
    """

    def inline_subscript_repl(self, stack, subscript, subscript_text):
        attrib = {moin_page.baseline_shift: "sub"}
        elem = moin_page.span(attrib=attrib, children=[subscript_text])
        stack.top_append(elem)

    inline_superscript = r"""
        (?P<superscript>
            \^
            (?P<superscript_text> .*? )
            \^
        )
    """

    def inline_superscript_repl(self, stack, superscript, superscript_text):
        attrib = {moin_page.baseline_shift: "super"}
        elem = moin_page.span(attrib=attrib, children=[superscript_text])
        stack.top_append(elem)

    inline_underline = r"""
        (?P<underline>
            __
        )
    """

    def inline_underline_repl(self, stack, underline):
        if not stack.top_check("ins"):
            stack.push(moin_page.ins())
        else:
            stack.pop()

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
                    (?P<link_interwiki_site>[a-zA-Z][a-zA-Z0-9]+)
                    :
                    (?P<link_interwiki_item>[^|]+) # accept any item name; will verify link_interwiki_site below
                )
                |
                (?P<link_item> [^|]+? )
            )
            \s*
            (
                [|]
                \s*
                (?P<link_text> [^|]*?|([^|]*?\{\{.*?\}\}[^|]*?) )
                \s*
            )?
            (
                [|]
                \s*
                (?P<link_args> [^|]*? )
                \s*
            )?
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
        link_args=None,
        link_interwiki_site=None,
        link_interwiki_item=None,
    ):
        """Handle all kinds of links."""
        attribs = {}
        query = []
        if link_args:
            link_args = parse_arguments(link_args)  # XXX needs different parsing
            for key in link_args.keys():
                if key in ("target", "title", "download", "class", "accesskey"):
                    attribs[html(key)] = link_args[key]
                if key[0] == "&":
                    query.append(f"{key[1:]}={link_args[key]}")

        if link_interwiki_site:
            if is_known_wiki(link_interwiki_site):
                link = Iri(scheme="wiki", authority=link_interwiki_site, path="/" + link_interwiki_item)
                attribs[xlink.href] = link
                element = moin_page.a(attrib=attribs)
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
            if "#" in link_item:
                try:
                    if link_item.startswith("#") and "/+convert/" in request.url:
                        # avoid traceback in link.py when converting moinwiki item to reST | HTML | Docbook
                        link_item = request.url.split("+convert/")[-1] + link_item
                except RuntimeError:  # CLI call has no valid request context
                    pass
                link_item, fragment = link_item.rsplit("#", 1)
            else:
                link_item, fragment = link_item, None
            if "?" in link_item:
                path, link_query = link_item.rsplit("?", 1)
                query.insert(0, link_query)
            else:
                path, link_query = link_item, None
            if query:
                query = "&" + "&".join(query)
            else:
                query = None
            target = Iri(scheme="wiki.local", path=path, query=query, fragment=fragment)
            text = link_item
        else:
            target = Iri(link_url)
            text = link_url
        attribs[xlink.href] = target
        element = moin_page.a(attrib=attribs)
        stack.push(element)
        if link_text:
            self.parse_inline(link_text, stack, self.inlinedesc_re)
        else:
            stack.top_append(text)
        stack.pop()

    inline_macro = r"""
        (?P<macro>
            <<
            (?P<macro_name> \w+ )
            (
                \(
                (?P<macro_args> .*? )
                \)
            )?
            \s*
            >>
        )
    """

    def inline_macro_repl(self, stack, macro, macro_name, macro_args=""):
        """Handles macros using the placeholder syntax."""
        elem = self.macro(macro_name, macro_args, macro)
        stack.top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
            |
            `
            (?P<nowiki_text_backtick> .*? )
            `
        )
    """

    def inline_nowiki_repl(self, stack, nowiki, nowiki_text=None, nowiki_text_backtick=None):
        if nowiki_text is not None:
            return stack.top_append(moin_page.samp(children=[nowiki_text]))
        # we must pass empty strings for moinwiki in > out conversions (@``DATE@ must not be converted to @DATE@)
        elif nowiki_text_backtick is not None:
            return stack.top_append(moin_page.code(children=[nowiki_text_backtick]))

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
                (?P<object_item> [^|]+? )
            )
            \s*
            (
                [|]
                \s*
                (?P<object_text> [^|]*? )
                \s*
            )?
            (
                [|]
                \s*
                (?P<object_args> .*? )
                \s*
            )?
            }}
        )
    """

    def inline_object_repl(self, stack, object, object_url=None, object_item=None, object_text=None, object_args=None):
        """Handles objects transcluded within the page."""
        if object_args:
            args = parse_arguments(object_args, parse_re=object_re).keyword
        else:
            args = {}
        query_keys = {}
        attrib = {}
        whitelist = ["width", "height", "class"]
        for attr, value in args.items():
            if attr.startswith("&"):
                query_keys[attr[1:]] = value
            elif attr in whitelist:
                attrib[html(attr)] = value
        if object_text:
            attrib[html.alt] = object_text
        if object_item is not None:
            # img tag
            query = urlencode(query_keys, encoding=CHARSET)
            # TODO: moin 1.9 needed this for an attached file; move functionality to scripts/migration/moin/import19.py
            att = "attachment:"
            if object_item.startswith(att):
                object_item = "/" + object_item[len(att) :]  # now we have a subitem
            target = Iri(scheme="wiki.local", path=object_item, query=query, fragment=None)
            attrib[xinclude.href] = target
            element = xinclude.include(attrib=attrib)
            stack.top_append(element)
        else:
            # object tag
            target = Iri(object_url)
            attrib[xlink.href] = target
            element = moin_page.object(attrib)
            stack.top_append(element)

    table = block_table

    tablerow = r"""
        (?P<cell>
            (?P<cell_marker>
                (\|\|)+
            )
            (
                <
                (?P<cell_args> ([^<])*? )
                >
            )?
            (?P<cell_text>
                (
                    (.*?                       # optional text before link or transclusion
                        (
                            ((\[\[) | (\{\{))  # start of link or transclusion
                            .*?
                            ((\]\]) | (\}\}))  # end of link or transclusion
                            .*?                # optional text after link or transclusion
                        )*?                    # there may be multiple links or transclusion within a cell
                        (?=((\|\|) | $))       # lookahead sees end of cell
                    )
                    |
                    .*?(?=(\|\|) | $)          # simple case, no transclusion or link in cell
                )*
            )
            (?=
                \|\|
                |
                $
            )
        )
    """

    def tablerow_cell_repl(self, stack, table, row, cell, cell_marker, cell_text, cell_args=None):

        def add_attr_to_style(attrib, attr):
            attr = attr.strip().encode("ascii", errors="backslashreplace").decode("unicode-escape")
            if not attr.endswith(";"):
                attr += ";"
            if attrib.get(moin_page("style"), ""):
                attrib[moin_page("style")] = attrib.get(moin_page("style"), "") + " " + attr
            else:
                attrib[moin_page("style")] = attr

        element = moin_page.table_cell()
        stack.push(element)

        if len(cell_marker) // 2 > 1:
            element.set(moin_page.number_columns_spanned, len(cell_marker) // 2)

        if cell_args:
            cell_args = _TableArguments()(cell_args)
            no_errors = True

            # any positional parameters will be errors;  retrieved as (key=None, value="some-positional-param");
            for key, value in cell_args.items():
                if key == "bgcolor":
                    if no_errors:
                        # avoid overriding error highlighting
                        add_attr_to_style(element.attrib, f"background-color: {value};")
                elif key == "rowbgcolor":
                    add_attr_to_style(row.attrib, f"background-color: {value};")
                elif key == "tablebgcolor":
                    add_attr_to_style(table.attrib, f"background-color: {value};")
                elif key == "width":
                    add_attr_to_style(element.attrib, f"width: {value};")
                elif key == "tablewidth":
                    add_attr_to_style(table.attrib, f"width: {value};")
                elif key == "caption":
                    table.insert(0, moin_page.caption(children=[value]))
                elif key == "tableclass":
                    table.attrib[moin_page("class")] = value + " moin-wiki-table"
                elif key == "rowclass":
                    row.attrib[moin_page("class")] = value
                elif key == "class":
                    element.attrib[moin_page("class")] = value
                elif key == "tablestyle":
                    add_attr_to_style(table.attrib, value)
                elif key == "rowstyle":
                    add_attr_to_style(row.attrib, value)
                elif key == "style":
                    if no_errors:
                        add_attr_to_style(element.attrib, value)
                elif key == "tableid":
                    table.attrib[moin_page("id")] = value
                elif key == "rowid":
                    row.attrib[moin_page("id")] = value
                elif key == "id":
                    element.attrib[moin_page("id")] = value
                elif key == "number-columns-spanned":
                    element.attrib[moin_page(key)] = value
                elif key == "number-rows-spanned":
                    element.attrib[moin_page(key)] = value
                else:
                    if key == "error" or key is None:
                        error = value
                    else:
                        error = key
                    cell_markup = cell.split(">")[0]
                    cell_markup = cell_markup.split("<")[1]
                    msg1 = _("Error:")
                    msg2 = _("is invalid within")
                    cell_text = '[ {} "{}" {} <{}>&nbsp;]<<BR>>{}'.format(msg1, error, msg2, cell_markup, cell_text)
                    if no_errors:
                        add_attr_to_style(element.attrib, "background-color: pink; color: black;")
                    no_errors = False

        self.parse_inline(cell_text, stack, self.inline_re)

        stack.pop_name("table-cell")

    header_footer_re = re.compile(header_footer_separator, re.X)

    # Block elements
    block = (block_line, block_comment, block_head, block_separator, block_macro, block_nowiki, block_table, block_text)
    block_re = re.compile("|".join(block), re.X | re.U | re.M)

    indent_re = re.compile(indent, re.X)

    inline = (
        inline_link,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_emphstrong,
        inline_comment,
        inline_size,
        inline_strike,
        inline_subscript,
        inline_superscript,
        inline_underline,
        inline_entity,
    )
    inline_re = re.compile("|".join(inline), re.X | re.U)

    # link text may have markup, excluding links
    inlinedesc = (
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_emphstrong,
        inline_comment,
        inline_size,
        inline_strike,
        inline_subscript,
        inline_superscript,
        inline_underline,
        inline_entity,
    )
    inlinedesc_re = re.compile("|".join(inlinedesc), re.X | re.U)

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
        data = {str(k): v for k, v in match.groupdict().items() if v is not None}
        func = f"{prefix}_{match.lastgroup}_repl"
        # logging.debug("calling %s(%r, %r)" % (func, args, data))
        getattr(self, func)(*args, **data)

    def parse_block(self, iter_content, arguments):
        attrib = {}
        if arguments:
            for key, value in arguments.keyword.items():
                if key in ("style", "class"):
                    attrib[moin_page(key)] = value

        body = moin_page.body(attrib=attrib)
        stack = _Stack(body, iter_content=iter_content)

        for line in iter_content:
            data = {str(k): v for k, v in self.indent_re.match(line).groupdict().items() if v is not None}
            self.indent_repl(iter_content, stack, line, **data)

        return body

    def parse_inline(self, text, stack, inline_re):
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


default_registry.register(Converter.factory, type_moin_wiki, type_moin_document)
default_registry.register(Converter.factory, Type("x-moin/format;name=wiki"), type_moin_document)
