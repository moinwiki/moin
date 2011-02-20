# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Creole input converter

    See http://wikicreole.org/ for latest specs.

    Notes:
    * No markup allowed in headings.
      Creole 1.0 does not require us to support this.
    * No markup allowed in table headings.
      Creole 1.0 does not require us to support this.
    * No (non-bracketed) generic url recognition: this is "mission impossible"
      except if you want to risk lots of false positives. Only known protocols
      are recognized.
    * We do not allow ":" before "//" italic markup to avoid urls with
      unrecognized schemes (like wtf://server/path) triggering italic rendering
      for the rest of the paragraph.

    @copyright: 2007 MoinMoin:RadomirDopieralski (creole 0.5 implementation),
                2007 MoinMoin:ThomasWaldmann (updates)
                2008-2010 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from MoinMoin import wikiutil
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink, xinclude

from ._args_wiki import parse as parse_arguments
from ._wiki_macro import ConverterMacro

class _Iter(object):
    """
    Iterator with push back support

    Collected items can be pushed back into the iterator and further calls will
    return them.
    """

    def __init__(self, parent):
        self.__finished = False
        self.__parent = iter(parent)
        self.__prepend = []

    def __iter__(self):
        return self

    def next(self):
        if self.__finished:
            raise StopIteration

        if self.__prepend:
            return self.__prepend.pop(0)

        try:
            return self.__parent.next()
        except StopIteration:
            self.__finished = True
            raise

    def push(self, item):
        self.__prepend.append(item)

class _Stack(list):
    def clear(self):
        del self[1:]

    def pop_name(self, *names):
        """
        Remove anything from the stack including the given node.
        """
        while len(self) > 2 and not self.top_check(*names):
            self.pop()
        self.pop()

    def push(self, elem):
        self.top_append(elem)
        self.append(elem)

    def top(self):
        return self[-1]

    def top_append(self, elem):
        self[-1].append(elem)

    def top_append_ifnotempty(self, elem):
        if elem:
            self.top_append(elem)

    def top_check(self, *names):
        """
        Checks if the name of the top of the stack matches the parameters.
        """
        tag = self[-1].tag
        return tag.uri == moin_page.namespace and tag.name in names

class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        iter_content = _Iter(content)

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
        element = moin_page.h(attrib=attrib, children=(head_text, ))
        stack.top_append(element)

    # Matches an empty (only whitespaces) line.
    block_line = r'(?P<line> ^ \s* $ )'

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
            self._apply(match, 'list', iter_content, stack)

            if match.group('end') is not None:
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
                (?P<macro_args> .*?)
                \)
            )?
            \s*
            (
                [|]
                \s*
                (?P<macro_text> .+?)
                \s*
            )?
            >>
        )
        \s*
        $
    """

    def block_macro_repl(self, _iter_content, stack, macro, macro_name,
            macro_args=None, macro_text=None):
        """Handles macros using the placeholder syntax."""
        stack.clear()

        if macro_args:
            macro_args = parse_arguments(macro_args)
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
        "Unescaping generator for the lines in a nowiki block"

        for line in iter_content:
            match = self.nowiki_end_re.match(line)
            if match:
                if not match.group('escape'):
                    return
                line = match.group('rest')
            yield line

    def block_nowiki_repl(self, iter_content, stack, nowiki):
        "Handles a complete nowiki block"

        stack.clear()

        try:
            firstline = iter_content.next()
        except StopIteration:
            stack.push(moin_page.blockcode())
            return

        # Stop directly if we got an end marker in the first line
        match = self.nowiki_end_re.match(firstline)
        if match and not match.group('escape'):
            stack.push(moin_page.blockcode())
            return

        lines = _Iter(self.block_nowiki_lines(iter_content))

        match = self.nowiki_interpret_re.match(firstline)

        if match:
            name = match.group('nowiki_name')
            args = match.group('nowiki_args')
            if args:
                args = parse_arguments(args)

            # Parse it directly if the type is ourself
            if not name or name == 'creole':
                body = self.parse_block(lines, args)
                elem = moin_page.page(children=(body, ))
                stack.top_append(elem)

            else:
                stack.top_append(self.parser(name, args, lines))

        else:
            elem = moin_page.blockcode(children=(firstline, ))
            stack.top_append(elem)

            for line in lines:
                elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* ---- \s* $ )'

    def block_separator_repl(self, _iter_content, stack, separator):
        stack.clear()
        stack.top_append(moin_page.separator())

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

            self.block_table_row(match.group('table'), stack)

        stack.clear()

    def block_table_row(self, content, stack):
        element = moin_page.table_row()
        stack.push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, 'tablerow', stack)

        stack.pop()

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check('table', 'table-body', 'list'):
            stack.clear()

        if stack.top_check('body'):
            element = moin_page.p()
            stack.push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            stack.top_append('\n')
        self.parse_inline(text, stack)

    inline_emph = r'(?P<emph> (?<!:)// )'
    # there must be no : in front of the // avoids italic rendering in urls
    # with unknown protocols

    def inline_emph_repl(self, stack, emph):
        if not stack.top_check('emphasis'):
            stack.push(moin_page.emphasis())
        else:
            stack.pop_name('emphasis')

    inline_strong = r'(?P<strong> \*\* )'

    def inline_strong_repl(self, stack, strong):
        if not stack.top_check('strong'):
            stack.push(moin_page.strong())
        else:
            stack.pop_name('strong')

    inline_linebreak = r'(?P<linebreak> \\\\ )'

    def inline_linebreak_repl(self, stack, linebreak):
        element = moin_page.line_break()
        stack.top_append(element)

    inline_escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'

    def inline_escape_repl(self, stack, escape, escaped_char):
        stack.top_append(escaped_char)

    inline_link = r"""
        (?P<link>
            \[\[
            \s*
            (
                (?P<link_url>
                    [a-zA-Z0-9+.-]+
                    ://
                    [^|]+?
                )
                |
                (?P<link_page> [^|]+? )
            )
            \s*
            ([|] \s* (?P<link_text>.+?) \s*)?
            \]\]
        )
    """

    def inline_link_repl(self, stack, link, link_url=None, link_page=None, link_text=None):
        """Handle all kinds of links."""

        if link_page is not None:
            att = 'attachment:' # moin 1.9 needed this for an attached file
            if link_page.startswith(att):
                link_page = '/' + link_page[len(att):] # now we have a subitem
            target = unicode(Iri(scheme='wiki.local', path=link_page))
            text = link_page
        else:
            target = link_url
            text = link_url
        element = moin_page.a(attrib={xlink.href: target})
        stack.push(element)
        self.parse_inline(link_text or text, stack, self.link_desc_re)
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
            (
                [|]
                \s*
                (?P<macro_text> .+?)
                \s*
            )?
            >>
        )
    """

    def inline_macro_repl(self, stack, macro, macro_name,
            macro_args=None, macro_text=None):
        """Handles macros using the placeholder syntax."""

        if macro_args:
            macro_args = parse_arguments(macro_args)
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
        stack.top_append(moin_page.code(children=(nowiki_text, )))

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

        if object_page is not None:
            att = 'attachment:' # moin 1.9 needed this for an attached file
            if object_page.startswith(att):
                object_page = '/' + object_page[len(att):] # now we have a subitem
            target = Iri(scheme='wiki.local', path=object_page)
            text = object_page

            attrib = {xinclude.href: target}
            element = xinclude.include(attrib=attrib)
            stack.top_append(element)

        else:
            target = object_url
            text = object_url

            element = moin_page.object({xlink.href: target})
            stack.push(element)
            self.parse_inline(object_text or text, stack, self.link_desc_re)
            stack.pop()

    inline_url = r"""
        (?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<escaped_url>~)?
            (?P<url_target>
                # TODO: config.url_schemas
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )
    """

    def inline_url_repl(self, stack, url, url_target, escaped_url=None):
        """Handle raw urls in text."""

        if not escaped_url:
            # this url is NOT escaped
            attrib = {xlink.href: url_target}
            element = moin_page.a(attrib=attrib, children=(url_target, ))
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
            if cur.tag.name == 'body':
                break
            if cur.tag.name == 'list-item-body':
                if list_level > cur.list_level:
                    break
            if cur.tag.name == 'list':
                if list_level >= cur.list_level and list_type == cur.list_type:
                    break
            stack.pop()

        if cur.tag.name != 'list':
            generate = list_type == '#' and 'ordered' or 'unordered'
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
            (?P<cell_text> [^|]+ )
            \s*
        )
    """

    def tablerow_cell_repl(self, stack, cell, cell_text, cell_head=None):
        element = moin_page.table_cell()
        stack.push(element)

        # TODO: How to handle table headings
        self.parse_inline(cell_text, stack)

        stack.pop_name('table-cell')

    # Block elements
    block = (
        block_line,
        block_head,
        block_separator,
        block_macro,
        block_nowiki,
        block_list,
        block_table,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U)

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
        inline_linebreak,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    # Link description
    link_desc = (
        inline_object,
        inline_linebreak,
    )
    link_desc_re = re.compile('|'.join(link_desc), re.X | re.U)

    # List items
    list = (
        list_end,
        list_item,
        list_text,
    )
    list_re = re.compile('|'.join(list), re.X | re.U)

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
        data = dict(((k, v) for k, v in match.groupdict().iteritems() if v is not None))
        getattr(self, '%s_%s_repl' % (prefix, match.lastgroup))(*args, **data)

    def parse_block(self, iter_content, arguments):
        attrib = {}
        if arguments:
            for key, value in arguments.keyword.iteritems():
                if key in ('style', ):
                    attrib[moin_page(key)] = value

        body = moin_page.body(attrib=attrib)

        stack = _Stack([body])

        # Please note that the iterator can be modified by other functions
        for line in iter_content:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter_content, stack)

        return body

    def parse_inline(self, text, stack, inline_re=inline_re):
        """Recognize inline elements within the given text"""

        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            stack.top_append_ifnotempty(text[pos:match.start()])
            pos = match.end()

            self._apply(match, 'inline', stack)

        # Handle trailing text
        stack.top_append_ifnotempty(text[pos:])

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document, type_moin_creole
default_registry.register(Converter.factory, type_moin_creole, type_moin_document)
default_registry.register(Converter.factory, Type('x-moin/format;name=creole'), type_moin_document)
