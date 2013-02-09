# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro and pseudo-macro handling

Base class for wiki parser with macro support.
"""

from MoinMoin import log
logging = log.getLogger(__name__)

from emeraldtree import ElementTree as ET

from MoinMoin.util import iri
from MoinMoin.util.mime import Type
from MoinMoin.util.tree import moin_page, xinclude

class ConverterMacro(object):
    def _BR_repl(self, args, text, context_block):
        if context_block:
            return
        return moin_page.line_break()

    def _FootNote_repl(self, args, text, context_block):
        if not args:
            # return a minimal note elem to indicate explicit footnote placement
            elem = moin_page.note()
            return elem

        text = self.macro_text(' '.join(args.positional))
        elem_body = moin_page.note_body(children=text)
        attrib = {moin_page.note_class: 'footnote'}
        elem = moin_page.note(attrib=attrib, children=[elem_body])

        if context_block:
            return moin_page.p(children=[elem])
        return elem

    def _Include_repl(self, args, text, context_block):
        if not context_block:
            return text

        pagename = args[0]
        heading = None # TODO
        level = None # TODO
        sort = 'sort' in args and args['sort']
        if sort and sort not in ('ascending', 'descending'):
            raise RuntimeError
        items = 'items' in args and int(args['items'])
        skipitems = 'skipitems' in args and int(args['skipitems'])
        titlesonly = 'titlesonly' in args
        editlink = 'editlink' in args

        attrib = {}
        xpointer = []
        xpointer_moin = []

        def add_moin_xpointer(function, args):
            args = unicode(args).replace('^', '^^').replace('(', '^(').replace(')', '^)')
            xpointer_moin.append(function + u'(' + args + u')')

        moin_args = []

        if pagename.startswith(u'^'):
            add_moin_xpointer(u'pages', pagename)
            if sort:
                add_moin_xpointer(u'sort', sort)
            if items:
                add_moin_xpointer(u'items', items)
            if skipitems:
                add_moin_xpointer(u'skipitems', skipitems)
        else:
            link = iri.Iri(scheme=u'wiki.local', path=pagename)
            attrib[xinclude.href] = link

        if heading is not None:
            add_moin_xpointer(u'heading', heading)
        if level:
            add_moin_xpointer(u'level', str(level))
        if titlesonly:
            add_moin_xpointer(u'titlesonly')
        if editlink:
            add_moin_xpointer(u'editlink')

        if xpointer_moin:
            xpointer.append(u'page:include({0})'.format(u' '.join(xpointer_moin)))

        if xpointer:
            # TODO: Namespace?
            ns = 'xmlns(page={0}) '.format(moin_page)

            attrib[xinclude.xpointer] = ns + ' '.join(xpointer)

        return xinclude.include(attrib=attrib)

    def _TableOfContents_repl(self, args, text, context_block):
        if not context_block:
            return text

        attrib = {}
        if args:
            try:
                level = int(args[0])
            except ValueError:
                pass
            else:
                attrib[moin_page.outline_level] = str(level)

        return moin_page.table_of_content(attrib=attrib)

    def macro(self, name, args, text, context_block=False):
        func = getattr(self, '_{0}_repl'.format(name), None)
        if func is not None:
            logging.debug("builtin macro: %r" % name)
            return func(args, text, context_block)

        logging.debug("extension macro: %r" % name)
        tag = context_block and moin_page.part or moin_page.inline_part

        elem = tag(attrib={
            moin_page.alt: text,
            moin_page.content_type: 'x-moin/macro;name=' + name,
        })

        if args:
            elem_arguments = moin_page.arguments()
            elem.append(elem_arguments)

            for key, value in args.items():
                attrib = {}
                if key:
                    attrib[moin_page.name] = key
                elem_arg = moin_page.argument(attrib=attrib, children=(value, ))
                elem_arguments.append(elem_arg)

        return elem

    def macro_text(self, text):
        """
        Should be overriden to format text in some macros according to the
        input type.
        :returns: Sequence of (ET.Element, unicode)
        """
        return [text]

    # TODO: Merge with macro support somehow.
    def parser(self, name, args, content):
        if '/' in name:
            type = Type(name)
        else:
            type = Type(type='x-moin', subtype='format', parameters={'name': name})
        logging.debug("parser type: %r" % (type, ))

        elem = moin_page.part(attrib={moin_page.content_type: type})

        if args:
            elem_arguments = moin_page.arguments()
            elem.append(elem_arguments)

            for key, value in args.items():
                attrib = {}
                if key:
                    attrib[moin_page.name] = key
                elem_arg = moin_page.argument(attrib=attrib, children=(value, ))
                elem_arguments.append(elem_arg)

        if content:
            elem.append(moin_page.body(children=content))

        return elem
