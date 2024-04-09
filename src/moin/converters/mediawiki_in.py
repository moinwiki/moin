# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:ReimarBauer
# Copyright: 2008-2010 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Media Wiki input converter
"""

import re
from html.entities import name2codepoint

from urllib.parse import urlencode

from moin.constants.contenttypes import CHARSET
from moin.constants.misc import URI_SCHEMES
from moin.utils.iri import Iri
from moin.utils.tree import moin_page, xlink
from moin.utils.mime import Type, type_moin_document

from . import default_registry
from ._args import Arguments
from ._wiki_macro import ConverterMacro
from ._util import decode_data, normalize_split_text, _Iter, _Stack

from moin import log

logging = log.getLogger(__name__)


class _TableArguments:
    rules = r"""
    (?:
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
        content = normalize_split_text(text)
        iter_content = _Iter(content)
        self.preprocessor = self.Mediawiki_preprocessor()
        body = self.parse_block(iter_content, arguments)
        root = moin_page.page(children=(body,))

        return root

    block_head = r"""
        (?P<head>
            ^
            \s*
            (?P<head_head> =+ )
            \s*
            (?P<head_text> .*? )
            \s*
            (?P=head_head)
            \s*
            $
        )
    """

    def block_head_repl(self, _iter_content, stack, head, head_head, head_text):
        stack.clear()

        attrib = {moin_page.outline_level: str(len(head_head))}
        element = moin_page.h(attrib=attrib, children=[head_text])
        stack.top_append(element)

    block_line = r"(?P<line> ^ \s* $ )"
    # empty line that separates paragraphs

    def block_line_repl(self, _iter_content, stack, line):
        stack.clear()

    block_separator = r"(?P<separator> ^ \s* -{4,} \s* $ )"

    def block_separator_repl(self, _iter_content, stack, separator):
        stack.clear()
        stack.top_append(moin_page.separator())

    block_table = r"""
        ^
        (?P<table>
            \{\|
            \s*
            (?P<table_args> .*?)
        )
        $
    """

    table_end = r"""
        ^
        (?P<table_end>
        \|\}
        \s*
        )
        $
    """

    def block_table_lines(self, iter_content):
        """Unescaping generator for the lines in a table block"""
        for line in iter_content:
            match = self.table_end_re.match(line)
            if match:
                return
            yield line

    def block_table_repl(self, iter_content, stack, table, table_args=""):
        stack.clear()
        # TODO: table attributes
        elem = moin_page.table()
        stack.push(elem)
        if table_args:
            table_args = _TableArguments()(table_args)
            for key, value in table_args.keyword.items():
                attrib = elem.attrib
                if key in ("class", "style", "number-columns-spanned", "number-rows-spanned"):
                    attrib[moin_page(key)] = value

        element = moin_page.table_body()
        stack.push(element)
        lines = _Iter(self.block_table_lines(iter_content), startno=iter_content.lineno)
        element = moin_page.table_row()
        stack.push(element)
        preprocessor_status = []
        for line in lines:
            m = self.tablerow_re.match(line)
            if not m:
                return
            if m.group("newrow"):
                stack.pop_name("table-row")
                element = moin_page.table_row()
                stack.push(element)
            cells = m.group("cells")
            if cells:
                cells = cells.split("||")
                for cell in cells:
                    if stack.top_check("table-cell"):
                        stack.pop()

                    cell = re.split(r"\s*\|\s*", cell)
                    element = moin_page.table_cell()
                    if len(cell) > 1:
                        cell_args = _TableArguments()(cell[0])
                        for key, value in cell_args.keyword.items():
                            attrib = element.attrib
                            if key in ("class", "style", "number-columns-spanned", "number-rows-spanned"):
                                attrib[moin_page(key)] = value
                        cell = cell[1]
                    else:
                        cell = cell[0]
                    stack.push(element)
                    self.preprocessor.push()
                    self.parse_inline(cell, stack, self.inline_re)
                    preprocessor_status = self.preprocessor.pop()
            elif m.group("text"):
                self.preprocessor.push(preprocessor_status)
                self.parse_inline("\n{}".format(m.group("text")), stack, self.inline_re)
                preprocessor_status = self.preprocessor.pop()
        stack.pop_name("table")

    block_text = r"(?P<text> .+ )"

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check("table", "table-body", "list"):
            stack.clear()

        if stack.top_check("body", "list-item-body"):
            element = moin_page.p()
            stack.push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            stack.top_append("\n")
        self.parse_inline(text, stack, self.inline_re)

    indent = r"""
        ^
        (?P<indent> [*#:]* )
        (?P<list_begin>
            (?P<list_definition> ;
            )
            \s*
            |
            (?P<list_numbers> \# )
            \s+
            |
            (?P<list_bullet> \* )
            \s+
            |
            (?P<list_none> \: )
            \s+
        )
        (?P<text> .*? )
        $
    """

    def indent_iter(self, iter_content, line, level, is_list):
        yield line

        while True:
            try:
                line = next(iter_content)
            except StopIteration:
                return

            match = self.indent_re.match(line)

            new_level = 0
            if not match:
                if is_list:
                    iter_content.push(line)
                    return
                else:
                    yield line
                    break

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
        list_bullet=None,
        list_none=None,
    ):
        level = len(indent)
        list_type = "unordered", "none"
        if list_begin:
            if list_definition:
                list_type = "definition", None
            elif list_numbers:
                list_type = "ordered", None
            elif list_bullet:
                list_type = "unordered", None
            elif list_none:
                list_type = None, None

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
        if list_begin:
            if element_use.tag.name != "list":
                attrib = {}
                if not list_definition:
                    attrib[moin_page.item_label_generate] = list_type[0]
                if list_type[1]:
                    attrib[moin_page.list_style_type] = list_type[1]
                element = moin_page.list(attrib=attrib)
                element.level, element.list_type = level, list_type
                stack.push(element)

            stack.push(moin_page.list_item())
            if list_definition:
                element_label = moin_page.list_item_label()
                stack.top_append(element_label)
                new_stack = _Stack(element_label, iter_content=iter_content)
                # TODO: definition list doesn't work,
                #       if definition of the term on the next line
                splited_text = text.split(":")
                list_definition_text = splited_text.pop(0)
                text = ":".join(splited_text)

                self.parse_inline(list_definition_text, new_stack, self.inline_re)

            element_body = moin_page.list_item_body()
            element_body.level, element_body.type = level, type

            stack.push(element_body)
            new_stack = _Stack(element_body, iter_content=iter_content)
        else:
            new_stack = stack
            level = 0

        is_list = list_begin
        iter = _Iter(self.indent_iter(iter_content, text, level, is_list), startno=iter_content.lineno)
        for line in iter:
            match = self.block_re.match(line)
            it = iter
            # XXX: Hack to allow nowiki to ignore the list indentation
            if match.lastgroup == "table" or match.lastgroup == "nowiki":
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
                (?=\s)
            )
        )
    """

    def inline_comment_repl(self, stack, comment, comment_begin=None, comment_end=None):
        # TODO
        pass

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
                if stack.top_check("strong"):
                    stack.pop()
                else:
                    stack.push(moin_page.strong())
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
            c = chr(name2codepoint.get(entity[1:-1], 0xFFFE))
        stack.top_append(c)

    inline_blockquote = r"""
        (?P<blockquote>
            (?P<blockquote_begin>
            \<blockquote.*?\>
            )
            |
            (?P<blockquote_end>
            \<\/blockquote\>
            )
        )
    """

    def inline_blockquote_repl(self, stack, blockquote, blockquote_begin=None, blockquote_end=None):
        if blockquote_begin is not None:
            stack.push(moin_page.blockquote())
        elif blockquote_end is not None:
            stack.pop()

    inline_footnote = r"""
        (?P<footnote>
            (?P<footnote_begin>
            \<ref.*?\>
            )
            |
            (?P<footnote_end>
            \<\/ref\>
            )
        )
    """

    def inline_footnote_repl(
        self, stack, footnote, footnote_begin=None, footnote_text=None, footnote_end=None, footnote_start=None
    ):
        # stack.top_check('emphasis'):
        if footnote_begin is not None:
            stack.push(moin_page.note(attrib={moin_page.note_class: "footnote"}))
            stack.push(moin_page.note_body())
        elif footnote_end is not None:
            stack.pop()
            stack.pop()

    inline_strike = r"""
        (?P<strike>
           \<s\>
           |
           \<\/s\>
        )
    """

    def inline_strike_repl(self, stack, strike):
        if not stack.top_check("s"):
            stack.push(moin_page.s())
        else:
            stack.pop()

    inline_delete = r"""
        (?P<delete>
           \<del\>
           |
           \<\/del\>
        )
    """

    def inline_delete_repl(self, stack, delete):
        if not stack.top_check("del"):
            stack.push(moin_page.del_())
        else:
            stack.pop()

    inline_subscript = r"""
        (?P<subscript>
            <sub>
            (?P<subscript_text> .*? )
            </sub>
        )
    """

    def inline_subscript_repl(self, stack, subscript, subscript_text):
        attrib = {moin_page.baseline_shift: "sub"}
        elem = moin_page.span(attrib=attrib, children=[subscript_text])
        stack.top_append(elem)

    inline_superscript = r"""
        (?P<superscript>
            <sup>
            (?P<superscript_text> .*? )
            </sup>
        )
    """

    def inline_superscript_repl(self, stack, superscript, superscript_text):
        attrib = {moin_page.baseline_shift: "super"}
        elem = moin_page.span(attrib=attrib, children=[superscript_text])
        stack.top_append(elem)

    inline_underline = r"""
        (?P<underline>
            \<u\>
            |
            \<\/u\>
        )
    """

    def inline_underline_repl(self, stack, underline):
        if not stack.top_check("u"):
            stack.push(moin_page.u())
        else:
            stack.pop()

    inline_insert = r"""
        (?P<insert>
            \<ins\>
            |
            \<\/ins\>
        )
    """

    def inline_insert_repl(self, stack, insert):
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
                    [a-zA-Z0-9+.-]+
                    :
                    [^|]+?
                )
                |
                (?P<link_item> [^|]+? )
            )
            \s*
            (?P<link_args>
                (
                [|]
                \s*
                [^|]*?
                \s*
                )*
            )?
            \]\]
            |
            \[
            \s*
            (?P<external_link_url>
                    (%(uri_schemes)s)
                    :
                    [^ ]*
            )
            \s*
            (?P<alt_text> [^\]]*? )
            \s*
            \]
        )
    """ % dict(
        uri_schemes="|".join(URI_SCHEMES)
    )

    def parse_args(self, input):
        """
        Parses media wiki arguments, this is taken from _args_wiki > parse function. The primary difference
        being that mediawiki breaks on pipes whereas the default parser breaks on spaces. Apart from that
        this parser also supports a few extra characters such as "<, >, ., /", mostly for URL linking.

        :param input: can be like a|b|c=f|something else caption|g='long caption'|link=http://google.com
        :returns: Arguments instance
        """
        parse_rules = r"""
        (?:
            (?P<key>[\w-]+)=    # Matches 'key=' part of the string, optional
        )?
        (?:
            (?P<unquote_val>[-\w\s:\./<>]+) # Unquoted value, intended to break after a |
            |
            # Matches quoted values with every character, breaks after the quote
            "(?P<dquote_val>.*?)(?<!\\)"    # Quoted value with double quotes
            |
            '(?P<squote_val>.*?)(?<!\\)'    # Quoted value with single quotes
        )
        """
        parse_re = re.compile(parse_rules, re.X | re.U)
        ret = Arguments()
        for match in parse_re.finditer(input):
            key = match.group("key")
            value = match.group("unquote_val") or match.group("squote_val") or match.group("dquote_val")
            if key:
                ret.keyword[key] = value
            else:
                ret.positional.append(value)
        return ret

    def inline_link_repl(
        self, stack, link, link_url=None, link_item=None, link_args="", external_link_url=None, alt_text=""
    ):
        """Handle all kinds of links."""
        link_text = ""
        # Remove the first pipe/space, example of link_args : |arg1|arg2 or " arg1 arg2"
        parsed_args = self.parse_args(link_args[1:])
        query = None
        if parsed_args.keyword:
            query = urlencode(parsed_args.keyword, encoding=CHARSET)
        # Take the last of positional parameters as link_text(caption)
        if parsed_args.positional:
            link_text = parsed_args.positional.pop()
        if link_item is not None:
            if "#" in link_item:
                path, fragment = link_item.rsplit("#", 1)
            else:
                path, fragment = link_item, None
            target = Iri(scheme="wiki.local", path=path, query=query, fragment=fragment)
            text = link_item
        else:
            if link_url and len(link_url.split(":")) > 0 and link_url.split(":")[0] == "File":
                object_item = ":".join(link_url.split(":")[1:])
                args = parsed_args.keyword
                if object_item is not None:
                    if "do" not in args:
                        # by default, we want the item's get url for transclusion of raw data:
                        args["do"] = "get"
                    query = urlencode(args, encoding=CHARSET)
                    target = Iri(scheme="wiki.local", path=object_item, query=query, fragment=None)
                    text = object_item
                else:
                    target = Iri(scheme="wiki.local", path=link_url)
                    text = link_url

                if not link_text:
                    link_text = text
                attrib = {xlink.href: target}
                attrib[moin_page.alt] = link_text

                element = moin_page.object(attrib)
                stack.push(element)
                if link_text:
                    self.preprocessor.push()
                    self.parse_inline(link_text, stack, self.inlinedesc_re)
                    self.preprocessor.pop()
                else:
                    stack.top_append(text)
                stack.pop()
                return
            target = Iri(scheme="wiki.local", path=link_url)
            text = link_url
        if external_link_url:
            target = Iri(external_link_url)
            text = alt_text
        element = moin_page.a(attrib={xlink.href: target})
        stack.push(element)
        if link_text:
            self.preprocessor.push()
            self.parse_inline(link_text, stack, self.inlinedesc_re)
            self.preprocessor.pop()
        else:
            stack.top_append(text)
        stack.pop()

    inline_breakline = r"""
        (?P<breakline>
            \<br\ \/\>
        )
    """

    def inline_breakline_repl(self, stack, breakline):
        stack.top_append(moin_page.line_break())

    inline_nowiki = r"""
        (?P<nowiki>
            <nowiki>
            (?P<nowiki_text> .*? )
            </nowiki>
            |
            <pre>
            (?P<nowiki_text_pre> .*? )
            </pre>
            |
            <code>
            (?P<nowiki_text_code> .*? )
            </code>
            |
            <tt>
            (?P<nowiki_text_tt> .*? )
            </tt>
        )
    """

    def inline_nowiki_repl(
        self,
        stack,
        nowiki,
        nowiki_text=None,
        nowiki_text_pre=None,
        pre_args="",
        nowiki_text_code=None,
        nowiki_text_tt=None,
    ):
        text = None

        if nowiki_text is not None:
            text = nowiki_text
            stack.top_append(moin_page.code(children=[text]))
        elif nowiki_text_code is not None:
            text = nowiki_text_code
            stack.top_append(moin_page.code(children=[text]))
        elif nowiki_text_tt is not None:
            text = nowiki_text_tt
            stack.top_append(moin_page.code(children=[text]))
        # Remove empty backtick nowiki samples
        elif nowiki_text_pre:
            # TODO: pre_args parsing
            text = nowiki_text_pre
            stack.top_append(moin_page.blockcode(children=[text]))
        else:
            return

    table = block_table

    tablerow = r"""
        ^
        [|!]
        (?P<tablerow>
            (?P<caption> \+.* )
            |
            (?P<newrow> \-\s* )
            |
            (?P<cells> .* )
        )
        |
        (?P<text> .* )
        $
    """
    # Block elements
    block = (
        block_line,
        block_table,
        block_head,
        block_separator,
        # block_macro,
        # block_nowiki,
        block_text,
    )
    block_re = re.compile("|".join(block), re.X | re.U | re.M)

    indent_re = re.compile(indent, re.X)

    inline = (
        inline_link,
        inline_breakline,
        inline_blockquote,
        # inline_macro,
        inline_nowiki,
        # inline_object,
        inline_emphstrong,
        inline_comment,
        inline_footnote,
        # inline_size,
        inline_strike,
        inline_delete,
        inline_subscript,
        inline_superscript,
        inline_underline,
        inline_insert,
        inline_entity,
    )
    inline_re = re.compile("|".join(inline), re.X | re.U)

    inlinedesc = (
        # inline_macro,
        inline_breakline,
        inline_nowiki,
        inline_emphstrong,
    )
    inlinedesc_re = re.compile("|".join(inlinedesc), re.X | re.U)

    # Nowiki end
    # nowiki_end_re = re.compile(nowiki_end, re.X)

    # Table
    table_re = re.compile(table, re.X | re.U)
    table_end_re = re.compile(table_end, re.X)

    # Table row
    tablerow_re = re.compile(tablerow, re.X | re.U)

    class Mediawiki_preprocessor:

        class Preprocessor_tag:
            def __init__(self, name="", text="", tag="", status=True):
                self.tag_name = name
                self.tag = tag
                self.text = [text]
                self.status = status

        all_tags = ["br", "blockquote" "del", "pre", "code", "tt", "nowiki", "ref", "s", "sub", "sup"]

        nowiki_tags = ["pre", "code", "tt", "nowiki"]

        block_tags = ["blockquote"]

        def __init__(self):
            self.opened_tags = []
            self.nowiki = False
            self.nowiki_tag = ""
            self._stack = []

        def push(self, status=[]):
            self._stack.append(self.opened_tags)
            self.opened_tags = status
            if self.opened_tags:
                if self.opened_tags[-1].tag_name in self.nowiki_tags:
                    self.nowiki = True
                    self.nowiki_tag = self.opened_tags[-1].tag_name
                else:
                    self.nowiki = False
                    self.nowiki_tag = ""

        def pop(self):
            if len(self._stack):
                self.opened_tags = self._stack.pop()
            else:
                self.opened_tags = []
            if self.opened_tags:
                if self.opened_tags[-1].tag_name in self.nowiki_tags:
                    self.nowiki = True
                    self.nowiki_tag = self.opened_tags[-1].tag_name
                else:
                    self.nowiki = False
                    self.nowiki_tag = ""
            return self.opened_tags

        def __call__(self, line, tags=[]):
            tags = tags or self.opened_tags
            match = re.match(r"(.*?)(<.*>.*)|(.*)", line)
            if match:
                pre_text = match.group(1) or match.group(3)
                # text may be None
                if pre_text:
                    if len(tags):
                        tags[-1].text.append(pre_text)
                        post_line = []
                    else:
                        post_line = [pre_text]
                else:
                    post_line = []
                next_text = match.group(2)
                while next_text:
                    match = re.match(r"<\s*([^>]*)>(?:(.*?)(<[^>]*>.*)|(.*))", next_text)
                    if match:
                        tag = match.group(1)
                        next_text = match.group(3)
                        text = match.group(2) or match.group(4)
                        if not text:
                            text = ""
                        tag_match = re.match(r"/\s*(.*)", tag)
                        status = not tag_match
                        if tag_match:
                            tag_name = tag_match.group(1).split(" ")[0]
                        else:
                            tag_name = tag.split(" ")[0]
                        if (
                            tag_name not in self.all_tags
                            or re.match(r".*/\s*$", tag)
                            or self.nowiki
                            and (status or tag_name != self.nowiki_tag)
                        ):
                            if not len(tags):
                                post_line.append(f"<{tag}>")
                                post_line.append(text)
                            else:
                                tags[-1].text.append(f"<{tag}>")
                                tags[-1].text.append(text)
                        else:
                            if not status:
                                if self.nowiki:
                                    if tag_name == self.nowiki_tag:
                                        self.nowiki_tag = ""
                                        self.nowiki = False
                                if tag_name in [t.tag_name for t in tags]:
                                    open_tags = []
                                    tmp_line = ""
                                    close_tag = self.Preprocessor_tag()
                                    while tag_name != close_tag.tag_name:
                                        close_tag = tags.pop()
                                        tmp_line = "<{}>{}{}</{}>".format(
                                            close_tag.tag, "".join(close_tag.text), tmp_line, close_tag.tag_name
                                        )
                                        if not len(tags):
                                            post_line.append(tmp_line)
                                        else:
                                            tags[-1].text.append(tmp_line)
                                        open_tags.append(close_tag)
                                    open_tags = open_tags[:-1]
                                    if not len(tags):
                                        post_line.append(text)
                                    else:
                                        tags[-1].text.append(text)
                                    if open_tags:
                                        for t in open_tags[:-1].reverse():
                                            t.text = ""
                                            tags.append(t)
                            else:
                                if tag_name in self.nowiki_tags:
                                    self.nowiki = True
                                    self.nowiki_tag = tag_name
                                tags.append(self.Preprocessor_tag(tag_name, text, tag))
                    else:
                        post_line.append(next_text)
                        break
                return "".join(post_line)
            self.opened_tags = tags

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
                if key in ("style",):
                    attrib[moin_page(key)] = value
                elif key == "_old":
                    attrib[moin_page.class_] = value.replace("/", " ")

        body = moin_page.body(attrib=attrib)

        stack = _Stack(body, iter_content=iter_content)

        for line in iter_content:
            match = self.indent_re.match(line)
            if match:
                data = {str(k): v for k, v in match.groupdict().items() if v is not None}
                self.indent_repl(iter_content, stack, line, **data)
            else:
                self.indent_repl(iter_content, stack, line, "", line)

        return body

    def parse_inline(self, text, stack, inline_re):
        """Recognize inline elements within the given text"""
        lines = text.split("\n")
        text = []
        for line in lines:
            text.append(self.preprocessor(line))
        text = "\n".join(text)
        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            stack.top_append_ifnotempty(text[pos : match.start()])
            pos = match.end()

            self._apply(match, "inline", stack)

        # Handle trailing text
        stack.top_append_ifnotempty(text[pos:])


default_registry.register(Converter.factory, Type("x-moin/format;name=mediawiki"), type_moin_document)
default_registry.register(Converter.factory, Type("text/x-mediawiki"), type_moin_document)
