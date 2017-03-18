# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - NoWiki handling: {{{#!....}}}

Expands nowiki elements in an internal Moin document.
"""

from __future__ import absolute_import, division

from emeraldtree import ElementTree as ET

import pygments
from . pygments_in import TreeFormatter
from pygments.util import ClassNotFound

from MoinMoin.i18n import _, L_, N_
from MoinMoin.util.tree import moin_page

from ._table import TableMixin
from ._util import normalize_split_text, _Iter
from ._args_wiki import parse as parse_arguments

from MoinMoin import log
logging = log.getLogger(__name__)


common_highlighters = u'diff cplusplus python java pascal irc'.split()


class Converter(object):
    @classmethod
    def _factory(cls, input, output, nowiki=None, **kw):
        if nowiki == 'expandall':
            return cls()

    def handle_nowiki(self, elem, page):

        logging.debug("handle_nowiki elem: %r" % elem)
        marker_len, nowiki_args, content = elem._children
        arguments = parse_arguments(nowiki_args[0])
        nowiki_name = arguments.positional[0]
        nowiki_args_old = arguments.positional[1] if len(arguments.positional) > 1 else None
        # all the old children of the element will be removed and new children added
        elem.remove_all()
        lexer = None
        if nowiki_name == u'highlight':
            try:
                lexer = pygments.lexers.get_lexer_by_name(nowiki_args_old)
            except ClassNotFound:
                lexer = pygments.lexers.get_lexer_by_name('text')
        elif nowiki_name in common_highlighters:
            # support old highlighting markup as it was prior to moin 1.9
            lexer = pygments.lexers.get_lexer_by_name(nowiki_name)
        if lexer:
            blockcode = moin_page.blockcode(attrib={moin_page.class_: 'highlight'})
            pygments.highlight(content, lexer, TreeFormatter(), blockcode)
            elem.append(blockcode)
            return

        if nowiki_name in ('csv', 'text/csv'):
            # TODO: support moin 1.9 options: quotechar, show, hide, autofilter, name, link, static_cols, etc
            sep = nowiki_args_old or u';'
            content = content.split('\n')
            head = content[0].split(sep)
            rows = [x.split(sep) for x in content[1:]]
            csv_builder = TableMixin()
            table = csv_builder.build_dom_table(rows, head=head, cls='moin-csv-table moin-sortable')
            elem.append(table)
            return

        if nowiki_name in ('wiki', 'text/x.moin.wiki',):
            from .moinwiki_in import Converter as moinwiki_converter
            moinwiki = moinwiki_converter()
            lines = normalize_split_text(content)
            lines = _Iter(lines)
            if len(arguments.positional) > 1:
                arguments.keyword['class'] = u' '.join(arguments.positional[1:])
                del arguments.positional[1:]
            body = moinwiki.parse_block(lines, arguments)
            page = moin_page.page(children=(body, ))
            elem.append(page)
            return

        if nowiki_name in ('creole', 'text/x.moin.creole'):
            from .creole_in import Converter as creole_converter
            creole = creole_converter()
            lines = normalize_split_text(content)
            lines = _Iter(lines)
            body = creole.parse_block(lines, nowiki_args_old)
            page = moin_page.page(children=(body, ))
            elem.append(page)
            return

        if nowiki_name in ('rst', 'text/x-rst'):
            from .rst_in import Converter as rst_converter
            rst = rst_converter()
            page = rst(content, contenttype=u'text/x-rst;charset=utf-8')
            elem.append(page)
            return

        if nowiki_name in ('docbook', 'application/docbook+xml'):
            from .docbook_in import Converter as docbook_converter
            docbook = docbook_converter()
            page = docbook(content, contenttype=u'application/docbook+xml;charset=utf-8')
            elem.append(page)
            return

        if nowiki_name in ('markdown', 'text/x-markdown'):
            from .markdown_in import Converter as markdown_converter
            markdown = markdown_converter()
            page = markdown(content, contenttype=u'text/x-markdown;charset=utf-8')
            elem.append(page)
            return

        if nowiki_name in ('mediawiki', 'text/x-mediawiki'):
            from .mediawiki_in import Converter as mediawiki_converter
            mediawiki = mediawiki_converter()
            page = mediawiki(content, nowiki_args_old)
            elem.append(page)
            return

        elem.append(nowiki_name)
        elem.append(nowiki_args_old)
        elem.append(content)
        logging.error("Failed to process elem: %r" % elem)
        return

    def recurse(self, elem, page):
        if elem.tag in (moin_page.nowiki, ):
            yield elem, page

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page):
                    yield i

    def __call__(self, tree):
        for elem, page in self.recurse(tree, None):
            self.handle_nowiki(elem, page)
        return tree

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, type_moin_document, type_moin_document)
