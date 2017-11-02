# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Macro and pseudo-macro handling

Base class for wiki parser with macro support.
"""


from emeraldtree import ElementTree as ET

from MoinMoin.util import iri
from MoinMoin.util.mime import Type
from MoinMoin.util.tree import moin_page, xinclude
from ._args_wiki import parse as parse_arguments
from ._args_wiki import include_re
from MoinMoin.i18n import _, L_, N_

from MoinMoin import log
logging = log.getLogger(__name__)


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

        text = args[0]
        text = self.macro_text(text)  # footnotes may have markup, macro_text is likely overridden
        elem_body = moin_page.note_body(children=text)
        attrib = {moin_page.note_class: 'footnote'}
        elem = moin_page.note(attrib=attrib, children=[elem_body])

        if context_block:
            return moin_page.p(children=[elem])
        return elem

    def _Include_repl(self, args, text, context_block):
        """
        Return a moin_page node representing an include macro that will be processed
        further in /converter/include.py.

        The transclusion {{jpeg.jpg}} and the macro <<Include(jpeg.jpg)>> will have
        identical output.

        If context_block is true, the macro expansion will be enclosed in a DIV-tag, else the
        macro output will be enclosed in a SPAN-tag. converter/include.py will resolve
        HTML 5 validation issues should the macro output block tags within an inline context.
        """
        def error_message(msg):
            txt = moin_page.p(children=(text, ))
            msg = moin_page.p(children=(msg, ))
            msg.set(moin_page.class_, 'moin-error')
            div = moin_page.div(children=(txt, msg))
            return div

        if args:
            args = parse_arguments(args[0], parse_re=include_re)
        else:
            return error_message(_("Include Macro above has invalid format, missing item name"))
        pagename = args[0]
        heading = None
        level = None
        try:
            heading = args[1]
            level = int(args[2])
        except (IndexError, ValueError):
            pass
        sort = 'sort' in args and args['sort']
        if sort and sort not in ('ascending', 'descending'):
            return error_message(_("Include Macro above has invalid format, expected sort=ascending or descending"))
        # TODO: We need corresponding code in include.py to process items, skipitems, titlesonly, and editlink
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
            add_moin_xpointer(u'titlesonly', u'')
        if editlink:
            add_moin_xpointer(u'editlink', u'')

        if xpointer_moin:
            xpointer.append(u'page:include({0})'.format(u' '.join(xpointer_moin)))

        if xpointer:
            # TODO: Namespace?
            ns = 'xmlns(page={0}) '.format(moin_page)

            attrib[xinclude.xpointer] = ns + ' '.join(xpointer)

        span_wrap = xinclude.include(attrib=attrib)
        if not context_block:
            return span_wrap
        attrib = {moin_page.class_: 'moin-p'}
        return moin_page.div(attrib=attrib, children=[span_wrap])

    def _TableOfContents_repl(self, args, text, context_block):
        if not context_block:
            return text

        attrib = {}
        if args:
            try:
                level = int(args[0])
                assert 0 < level < 7
            except (ValueError, AssertionError):
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
