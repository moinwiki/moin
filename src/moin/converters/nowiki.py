# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - NoWiki handling: {{{#!....}}}

Expands nowiki elements in an internal Moin document.
"""

import re

from emeraldtree import ElementTree as ET

import pygments
from .pygments_in import TreeFormatter
from pygments.util import ClassNotFound

from moin.i18n import _
from moin.utils.tree import moin_page
from moin.utils.mime import type_moin_document

from . import default_registry
from ._args_wiki import parse as parse_arguments
from ._table import TableMixin
from ._util import normalize_split_text, _Iter

from moin import log

logging = log.getLogger(__name__)


class Converter:
    @classmethod
    def _factory(cls, input, output, nowiki=None, **kw):
        if nowiki == "expandall":
            return cls()

    def invalid_args(self, elem, all_nowiki_args):
        """Insert an error message into output."""
        message = _('Defaulting to plain text due to invalid arguments: "{arguments}"').format(
            arguments=all_nowiki_args[0]
        )
        admonition = moin_page.div(attrib={moin_page.class_: "error"}, children=[moin_page.p(children=[message])])
        elem.append(admonition)

    def handle_nowiki(self, elem, page):
        """{{{* where * may be #!wiki, #!csv, #!highlight python, "", etc., or an invalid argument."""
        logging.debug("handle_nowiki elem: %r" % elem)
        marker_len, all_nowiki_args, content = elem._children
        nowiki_args = all_nowiki_args[0].strip()

        # remove all the old children of the element, new children will be added
        elem.remove_all()

        if not nowiki_args:
            # input similar to: {{{\ntext\n}}}\n
            blockcode = moin_page.blockcode(children=(content,))
            elem.append(blockcode)
            return

        if nowiki_args.startswith("#!") and len(nowiki_args) > 2:
            arguments = nowiki_args[2:].split(" ", 1)  # skip leading #!
            nowiki_name = arguments[0]
            optional_args = arguments[1] if len(arguments) > 1 else None
        else:
            nowiki_name = optional_args = None

        lexer = None
        if nowiki_name in {"diff", "cplusplus", "python", "java", "pascal", "irc"}:
            # make old style markup similar to {{{#!python like new style {{{#!highlight python
            optional_args = nowiki_name if not optional_args else nowiki_name + " " + optional_args
            nowiki_name = "highlight"

        if nowiki_name == "highlight":
            # TODO: support moin 1.9 options like numbers=on start=222 step=10
            optional_args = optional_args.split()[0]  # ignore all parameters except lexer name
            try:
                lexer = pygments.lexers.get_lexer_by_name(optional_args)
            except ClassNotFound:
                try:
                    lexer = pygments.lexers.get_lexer_for_mimetype(optional_args)
                except ClassNotFound:
                    self.invalid_args(elem, all_nowiki_args)
                    lexer = pygments.lexers.get_lexer_by_name("text")
        if lexer:
            blockcode = moin_page.blockcode(attrib={moin_page.class_: "highlight"})
            pygments.highlight(content, lexer, TreeFormatter(), blockcode)
            elem.append(blockcode)
            return

        if nowiki_name in ("csv", "text/csv"):
            # TODO: support moin 1.9 options: quotechar, show, hide, autofilter, name, link, static_cols, etc
            delim = None
            if optional_args:
                m = re.search("delimiter=(.?)", optional_args)
                if m and m.group(1):
                    delim = m.group(1)
                if not delim:
                    delim = optional_args.split()[0]  # ignore all parameters except a delimiter in first position
                    if len(delim) > 1:
                        delim = None
            sep = delim or ";"
            content = content.split("\n")
            head = content[0].split(sep)
            rows = [x.split(sep) for x in content[1:]]
            csv_builder = TableMixin()
            table = csv_builder.build_dom_table(rows, head=head, cls="moin-csv-table moin-sortable")
            elem.append(table)
            return

        if nowiki_name in ("wiki", "text/x.moin.wiki"):
            from .moinwiki_in import Converter as moinwiki_converter

            moinwiki = moinwiki_converter()
            lines = normalize_split_text(content)
            lines = _Iter(lines)
            # reparse arguments from original: {{{#!wiki solid/orange (style="color: red;")
            wiki_args = parse_arguments(all_nowiki_args[0][2:])
            if len(wiki_args.positional) > 1:
                wiki_args.keyword["class"] = " ".join(wiki_args.positional[1:])
            del wiki_args.positional[:]
            body = moinwiki.parse_block(lines, wiki_args)
            page = moin_page.page(children=(body,))
            elem.append(page)
            return

        if nowiki_name in ("creole", "text/x.moin.creole"):
            from .creole_in import Converter as creole_converter

            creole = creole_converter()
            lines = normalize_split_text(content)
            lines = _Iter(lines)
            body = creole.parse_block(lines, optional_args)
            page = moin_page.page(children=(body,))
            elem.append(page)
            return

        if nowiki_name in ("rst", "text/x-rst"):
            from .rst_in import Converter as rst_converter

            rst = rst_converter()
            page = rst(content, contenttype="text/x-rst;charset=utf-8")
            elem.append(page)
            return

        if nowiki_name in ("docbook", "application/docbook+xml"):
            from .docbook_in import Converter as docbook_converter

            docbook = docbook_converter()
            page = docbook(content, contenttype="application/docbook+xml;charset=utf-8")
            elem.append(page)
            return

        if nowiki_name in ("markdown", "text/x-markdown"):
            from .markdown_in import Converter as markdown_converter

            markdown = markdown_converter()
            page = markdown(content, contenttype="text/x-markdown;charset=utf-8")
            elem.append(page)
            return

        if nowiki_name in ("mediawiki", "text/x-mediawiki"):
            from .mediawiki_in import Converter as mediawiki_converter

            mediawiki = mediawiki_converter()
            page = mediawiki(content, optional_args)
            elem.append(page)
            return

        if nowiki_name in ("html", "HTML", "text/html"):
            from .html_in import Converter as html_converter

            html = html_converter()
            page = html(content, optional_args)
            elem.append(page)
            return

        self.invalid_args(elem, all_nowiki_args)
        lexer = pygments.lexers.get_lexer_by_name("text")
        blockcode = moin_page.blockcode(attrib={moin_page.class_: "highlight"})
        pygments.highlight(content, lexer, TreeFormatter(), blockcode)
        elem.append(blockcode)
        return

    def recurse(self, elem, page):
        if elem.tag in (moin_page.nowiki,):
            yield elem, page

        for child in elem:
            if isinstance(child, ET.Node):
                yield from self.recurse(child, page)

    def __call__(self, tree):
        for elem, page in self.recurse(tree, None):
            self.handle_nowiki(elem, page)
        return tree


default_registry.register(Converter._factory, type_moin_document, type_moin_document)
