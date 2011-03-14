# Copyright: Docutils:David Goodger <goodger@python.org>
# Copyright: 2004 Matthew Gilbert <gilbert AT voxmea DOT net>
# Copyright: 2004 Alexander Schremmer <alex AT alexanderweb DOT de>
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - ReStructured Text input converter

It's based on docutils rst parser.
Conversion of docutils document tree to moinmoin document tree.

This converter based on ReStructuredText 2006-09-22.
Works with docutils version 0.5 (2008-06-25) or higher.
"""


from __future__ import absolute_import

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import g as flaskg

from MoinMoin import config, wikiutil
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xlink

#### TODO: try block
from docutils import nodes, utils, writers, core
from docutils.parsers.rst import Parser
from docutils.nodes import reference, literal_block
from docutils.parsers import rst
from docutils.parsers.rst import directives, roles
#####

class NodeVisitor(object):
    """
    Part of docutils which converts docutils DOM tree to Moin DOM tree
    """

    def __init__(self):
        self.current_node = moin_page.body()
        self.root = moin_page.page(children=(self.current_node, ))
        self.path = [self.root, self.current_node]
        self.header_size = 1
        self.status = ['document']
        self.footnotes = dict()

    def dispatch_visit(self, node):
        """
        Call self."``visit_`` + node class name" with `node` as
        parameter.  If the ``visit_...`` method does not exist, call
        self.unknown_visit.
        """
        node_name = node.__class__.__name__
        method = getattr(self, 'visit_' + node_name, self.unknown_visit)
        return method(node)

    def dispatch_departure(self, node):
        """
        Call self."``depart_`` + node class name" with `node` as
        parameter.  If the ``depart_...`` method does not exist, call
        self.unknown_departure.
        """
        node_name = node.__class__.__name__
        method = getattr(self, 'depart_' + node_name, self.unknown_departure)
        return method(node)

    def unknown_visit(self, node):
        """
        Called when entering unknown `Node` types.

        Raise an exception unless overridden.
        """
        pass

    def unknown_departure(self, node):
        """
        Called before exiting unknown `Node` types.

        Raise exception unless overridden.
        """
        pass

    def open_moin_page_node(self, mointree_element):
        self.current_node.append(mointree_element)
        self.current_node = mointree_element
        self.path.append(mointree_element)

    def close_moin_page_node(self):
        self.path.pop()
        self.current_node = self.path[-1]

    def tree(self):
        return self.root

    def visit_Text(self, node):
        text = node.astext()
        self.current_node.append(text)

    def depart_Text(self, node):
        pass

    def visit_admonition(self, node):
        self.open_moin_page_node(moin_page.admonition())

    def depart_admonition(self, node=None):
        self.close_moin_page_node()

    visit_note = visit_admonition
    visit_important = visit_admonition
    visit_danger = visit_admonition
    visit_caution = visit_admonition
    visit_attention = visit_admonition
    visit_tip = visit_admonition
    visit_warning = visit_admonition

    depart_note = depart_admonition
    depart_important = depart_admonition
    depart_danger = depart_admonition
    depart_caution = depart_admonition
    depart_attention = depart_admonition
    depart_tip = depart_admonition
    depart_warning = depart_admonition

    def visit_error(self, node):
        self.open_moin_page_node(moin_page.error())

    def depart_error(self, node=None):
        self.close_moin_page_node()

    def visit_block_quote(self, node):
        self.open_moin_page_node(moin_page.list())
        self.open_moin_page_node(moin_page.list_item())
        self.open_moin_page_node(moin_page.list_item_body())

    def depart_block_quote(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_bullet_list(self, node):
        self.open_moin_page_node(moin_page.list(
                        attrib={moin_page.item_label_generate: u'unordered'}))

    def depart_bullet_list(self, node):
        self.close_moin_page_node()

    def visit_definition(self, node):
        self.open_moin_page_node(moin_page.list_item_body())

    def depart_definition(self, node):
        self.close_moin_page_node()

    def visit_definition_list(self, node):
        self.open_moin_page_node(moin_page.list())

    def depart_definition_list(self, node):
        self.close_moin_page_node()

    def visit_definition_list_item(self, node):
        self.open_moin_page_node(moin_page.list_item())

    def depart_definition_list_item(self, node):
        self.close_moin_page_node()

    def visit_docinfo(self, node):
        self.open_moin_page_node(moin_page.table())
        self.open_moin_page_node(moin_page.table_body())

    def depart_docinfo(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_author(self, node):
        self.open_moin_page_node(moin_page.table_row())
        self.open_moin_page_node(moin_page.table_cell())
        self.open_moin_page_node(moin_page.strong())
        # TODO: i18n for docutils:
        self.open_moin_page_node(u"Author:")
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.open_moin_page_node(moin_page.table_cell())

    def depart_author(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_version(self, node):
        self.open_moin_page_node(moin_page.table_row())
        self.open_moin_page_node(moin_page.table_cell())
        self.open_moin_page_node(moin_page.strong())
        # TODO: i18n for docutils:
        self.open_moin_page_node(u"Version:")
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.open_moin_page_node(moin_page.table_cell())

    def depart_version(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_copyright(self, node):
        self.open_moin_page_node(moin_page.table_row())
        self.open_moin_page_node(moin_page.table_cell())
        self.open_moin_page_node(moin_page.strong())
        # TODO: i18n for docutils:
        self.open_moin_page_node(u"Copyright:")
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.open_moin_page_node(moin_page.table_cell())

    def depart_copyright(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_emphasis(self, node):
        self.open_moin_page_node(moin_page.emphasis())

    def depart_emphasis(self, node):
        self.close_moin_page_node()

    def visit_entry(self, node):
        new_element = moin_page.table_cell()
        if 'morerows' in node.attributes:
            new_element.set(moin_page.number_rows_spanned,
                            repr(int(node['morerows'])+1))
        if 'morecols' in node.attributes:
            new_element.set(moin_page.number_cols_spanned,
                            repr(int(node['morecols'])+1))
        self.open_moin_page_node(new_element)

    def depart_entry(self, node):
        self.close_moin_page_node()

    def visit_enumerated_list(self, node):
        enum_style = {'arabic': None,
                'loweralpha': u'lower-alpha',
                'upperalpha': u'upper-alpha',
                'lowerroman': u'lower-roman',
                'upperroman': u'upper-roman'}
        new_node = moin_page.list(
                attrib={moin_page.item_label_generate: u'ordered'})
        type = enum_style.get(node['enumtype'], None)
        if type:
            new_node.set(moin_page.list_style_type, type)
        self.open_moin_page_node(new_node)

    def depart_enumerated_list(self, node):
        self.close_moin_page_node()

    def visit_field(self, node):
        self.open_moin_page_node(moin_page.table_row())

    def depart_field(self, node):
        self.close_moin_page_node()

    def visit_field_body(self, node):
        self.open_moin_page_node(moin_page.table_cell())

    def depart_field_body(self, node):
        self.close_moin_page_node()

    def visit_field_list(self, node):
        pass

    def depart_field_list(self, node):
        pass

    def visit_field_name(self, node):
        self.open_moin_page_node(moin_page.table_cell())
        self.open_moin_page_node(moin_page.strong())
        self.open_moin_page_node(u'%s:' % node.astext())
        node.children = []
        self.close_moin_page_node()

    def depart_field_name(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_figure(self, node):
        pass

    def depart_figure(self, node):
        pass

    def visit_footer(self, node):
        pass

    def depart_footer(self, node):
        pass

    def visit_footnote(self, node):
        self.status.append('footnote')

    def depart_footnote(self, node):
        self.status.pop()

    def visit_footnote_reference(self, node):
        self.open_moin_page_node(moin_page.note(
                            attrib={moin_page.note_class: u'footnote'}))
        new_footnote = moin_page.note_body()
        self.open_moin_page_node(new_footnote)
        self.footnotes[node.children[-1]] = new_footnote
        node.children = []

    def depart_footnote_reference(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_header(self, node):
        pass

    def depart_header(self, node):
        pass

    def visit_image(self, node):
        new_node = moin_page.object(attrib={xlink.href: node['uri']})
        # TODO: rewrite this more compact
        alt = node.get('alt', None)
        if alt:
            new_node.set(moin_page.alt, node['uri'])
        arg = node.get('width', u'')
        if arg:
            new_node.set(moin_page.width, arg)
        arg = node.get('height', u'')
        if arg:
            new_node.set(moin_page.height, arg)

        # TODO: there is no 'scale' attribute in moinwiki
        arg = node.get('scale', u'')
        if arg:
            new_node.set(moin_page.scale, arg)

        self.open_moin_page_node(new_node)

    def depart_image(self, node):
        self.close_moin_page_node()

    def visit_inline(self, node):
        pass

    def depart_inline(self, node):
        pass

    def visit_label(self, node):
        if self.status[-1] == 'footnote':
            self.footnote_lable = node.astext()
        node.children = []

    def depart_label(self, node):
        pass

    def visit_line(self, node):
        pass

    def depart_line(self, node):
        pass

    def visit_line_block(self, node):
        pass

    def depart_line_block(self, node):
        pass

    def visit_list_item(self, node):
        self.open_moin_page_node(moin_page.list_item())
        self.open_moin_page_node(moin_page.list_item_body())

    def depart_list_item(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_literal(self, node):
        self.open_moin_page_node(moin_page.code())
        self.open_moin_page_node(node.astext())
        node.children = []
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_literal_block(self, node):
        parser = node.get('parser', u'')
        if parser:
            named_args = re.findall(r"(\w+)=(\w+)", parser)
            simple_args = re.findall(r"(?:\s)\w+(?:\s|$)", parser)
            args = []
            for value in simple_args:
                args.append(moin_page.argument(children=[value]))
            for name, value in named_args:
                args.append(moin_page.argument(attrib={moin_page.name: name}, children=[value]))
            arguments = moin_page.arguments(children=args)
            self.open_moin_page_node(moin_page.part(children=[arguments], attrib={moin_page.content_type: "x-moin/format;name=%s" % parser.split(' ')[0]}))
        else:
            self.open_moin_page_node(moin_page.blockcode())

    def depart_literal_block(self, node):
        self.close_moin_page_node()

    def visit_paragraph(self, node):
        if self.status[-1] == 'footnote':
            footnote_node = self.footnotes.get(self.footnote_lable, None)
            if footnote_node:
                footnote_node.append(node.astext())
            node.children = []
        else:
            self.open_moin_page_node(moin_page.p())

    def depart_paragraph(self, node):
        if self.status[-1] == 'footnote':
            pass
        else:
            self.close_moin_page_node()

    def visit_problematic(self, node):
        pass

    def depart_problematic(self, node):
        pass

    def visit_reference(self, node):
        refuri = node.get('refuri', u'')
        if refuri.startswith(u'<<') and refuri.endswith(u'>>'): # moin macro
            macro_name = refuri[2:-2].split(u'(')[0]
            if macro_name == u"TableOfContents":
                arguments = refuri[2:-2].split(u'(')[1][:-1].split(u',')
                node = moin_page.table_of_content()
                self.open_moin_page_node(node)
                if arguments and arguments[0]:
                    node.set(moin_page.outline_level, arguments[0])
                return
            arguments = refuri[2:-2].split(u'(')[1][:-1].split(u',')
            self.open_moin_page_node(
                moin_page.part(
                    attrib={
                        moin_page.content_type:\
                            "x-moin/macro;name=%s" % macro_name, }))
            if arguments:
                self.open_moin_page_node(moin_page.arguments())
                for i in arguments:
                    self.open_moin_page_node(moin_page.argument(children=[i]))
                    self.close_moin_page_node()
                self.close_moin_page_node()
            self.open_moin_page_node(refuri)
            self.close_moin_page_node()
            return

        self.open_moin_page_node(moin_page.a(attrib={xlink.href: refuri}))

    def depart_reference(self, node):
        self.close_moin_page_node()

    def visit_row(self, node):
        self.open_moin_page_node(moin_page.table_row())

    def depart_row(self, node):
        self.close_moin_page_node()

    def visit_rubric(self, node):
        self.visit_paragraph(node)

    def depart_rubric(self, node):
        self.depart_paragraph(node)

    def visit_substitution_definition(self, node):
        node.children = []

    def depart_substitution_definition(self, node):
        pass

    def visit_section(self, node):
        self.header_size += 1

    def depart_section(self, node):
        self.header_size -= 1

    def visit_sidebar(self, node):
        pass

    def depart_sidebar(self, node):
        pass

    def visit_strong(self, node):
        self.open_moin_page_node(moin_page.strong())

    def depart_strong(self, node):
        self.close_moin_page_node()

    def visit_subscript(self, node):
        self.open_moin_page_node(
            moin_page.span(
                attrib={moin_page.baseline_shift: u'sub'}))

    def depart_subscript(self, node):
        self.close_moin_page_node()

    def visit_subtitle(self, node):
        self.header_size += 1
        self.open_moin_page_node(
            moin_page.h(
                attrib={moin_page.outline_level: repr(self.header_size)}))

    def depart_subtitle(self, node):
        self.header_size -= 1
        self.close_moin_page_node()

    def visit_superscript(self, node):
        self.open_moin_page_node(
            moin_page.span(
                attrib={moin_page.baseline_shift: u'super'}))

    def depart_superscript(self, node):
        self.close_moin_page_node()

    def visit_system_message(self, node):
        node.children = []

    def depart_system_message(self, node):
        pass

    def visit_table(self, node):
        self.open_moin_page_node(moin_page.table())

    def depart_table(self, node):
        self.close_moin_page_node()

    def visit_tbody(self, node):
        self.open_moin_page_node(moin_page.table_body())

    def depart_tbody(self, node):
        self.close_moin_page_node()

    def visit_term(self, node):
        self.open_moin_page_node(moin_page.list_item_label())

    def depart_term(self, node):
        self.close_moin_page_node()

    def visit_tgroup(self, node):
        # TODO: Color style of tbody
        pass

    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        self.open_moin_page_node(moin_page.table_header())

    def depart_thead(self, node):
        self.close_moin_page_node()

    def visit_title(self, node):
        self.open_moin_page_node(
            moin_page.h(
                attrib={moin_page.outline_level: repr(self.header_size)}))

    def depart_title(self, node):
        self.close_moin_page_node()

    def visit_topic(self, node):
        pass

    def depart_topic(self, node):
        pass

    def visit_title_reference(self, node):
        pass

    def depart_title_reference(self, node):
        pass

    def unimplemented_visit(self, node):
        pass


def walkabout(node, visitor):
    """
    This is tree traversal part of docutils without docutils logging.
    """
    call_depart = 1
    stop = 0
    try:
        try:
            visitor.dispatch_visit(node)
        except nodes.SkipNode:
            return stop
        except nodes.SkipDeparture:
            call_depart = 0
        children = node.children
        try:
            for child in children[:]:
                if walkabout(child, visitor):
                    stop = 1
                    break
        except nodes.SkipSiblings:
            pass
    except nodes.SkipChildren:
        pass
    except nodes.StopTraversal:
        stop = 1
    if call_depart:
        visitor.dispatch_departure(node)
    return stop


class Writer(writers.Writer):

    supported = ('moin-x-document')
    config_section = 'MoinMoin writer'
    config_section_dependencies = ('writers', )
    output = None
    visitor_attributes = []

    def translate(self):
        self.visitor = visitor = NodeVisitor(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.tree()


class MoinDirectives(object):
    """
    Class to handle all custom directive handling. This code is called as
    part of the parsing stage.
    """

    def __init__(self):

        # include MoinMoin pages
        directives.register_directive('include', self.include)

        # used for MoinMoin macros
        directives.register_directive('macro', self.macro)

        #used for MoinMoin tables of content
        directives.register_directive('contents', self.table_of_content)

        #used for MoinMoin parsers
        directives.register_directive('parser', self.parser)

        # disallow a few directives in order to prevent XSS
        # for directive in ('meta', 'include', 'raw'):
        for directive in ('meta', 'raw'):
            directives.register_directive(directive, None)

        # disable the raw role
        roles._roles['raw'] = None

        # As a quick fix for infinite includes we only allow a fixed number of
        # includes per page
        self.num_includes = 0
        self.max_includes = 10

    # Handle the include directive rather than letting the default docutils
    # parser handle it. This allows the inclusion of MoinMoin pages instead of
    # something from the filesystem.
    def include(self, name, arguments, options, content, lineno,
                content_offset, block_text, state, state_machine):
        # content contains the included file name

        # TODO: i18n for errors

        # Limit the number of documents that can be included
        if self.num_includes < self.max_includes:
            self.num_includes += 1
        else:
            lines = ["**Maximum number of allowed includes exceeded**"]
            state_machine.insert_input(lines, 'MoinDirectives')
            return []

        if content:
            macro = u'<<Include(%s)>>' % content[0]
        else:
            macro = u'<<Include()>>'
        ref = reference(macro, refuri=macro)
        return [ref]

    include.has_content = include.content = True
    include.option_spec = {}
    include.required_arguments = 1
    include.optional_arguments = 0

    # Add additional macro directive.
    # This allows MoinMoin macros to be used either by using the directive
    # directly or by using the substitution syntax. Much cleaner than using the
    # reference hack (`<<SomeMacro>>`_). This however simply adds a node to the
    # document tree which is a reference, but through a much better user
    # interface.
    def macro(self, name, arguments, options, content, lineno,
                content_offset, block_text, state, state_machine):
        # content contains macro to be called
        if len(content):
            # Allow either with or without brackets
            if content[0].startswith(u'<<'):
                macro = content[0]
            else:
                macro = u'<<%s>>' % content[0]
            ref = reference(macro, refuri=macro)
            ref['name'] = macro
            return [ref]
        return

    macro.has_content = macro.content = True
    macro.option_spec = {}
    macro.required_arguments = 1
    macro.optional_arguments = 0

    def table_of_content(self, name, arguments, options, content, lineno,
                            content_offset, block_text, state, state_machine):
        text = ''
        for i in content:
            m = re.search(r':(\w+): (\w+)', i)
            if m and len(m.groups()) == 2:
                if m.groups()[0] == u'depth':
                    text = m.groups()[1]
        macro = u'<<TableOfContents(%s)>>' % text
        ref = reference(macro, refuri=macro)
        ref['name'] = macro
        return [ref]

    table_of_content.has_content = table_of_content.content = True
    table_of_content.option_spec = {}
    table_of_content.required_arguments = 1
    table_of_content.optional_arguments = 0

    def parser(self, name, arguments, options, content, lineo,
                content_offset, block_text, state, state_machine):
        block = literal_block()
        block['parser'] = content[0]
        block.children = [nodes.Text(u"\n".join(content[1:]))]
        return [block]

    parser.has_content = parser.content = True
    parser.option_spec = {}
    parser.required_arguments = 1
    parser.optional_arguments = 0


class Converter(object):

    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, input, arguments=None):
        parser = MoinDirectives()
        while True:
            input = u'\n'.join(input)
            try:
                docutils_tree = core.publish_doctree(source=input)
            except utils.SystemMessage as inst:
                string_numb = re.match(re.compile(r'<string>\:([0-9]*)\:\s*\(.*?\)\s*(.*)', re.X | re.U | re.M | re.S), str(inst))
                if string_numb:
                    str_num = string_numb.group(1)
                    input = input.split('\n')
                    if str_num:
                        input = ['.. error::\n ::\n\n  Parse error on line number %s:\n\n  %s\n\n  Go back and try fix that.\n\n' % (str_num, string_numb.group(2).replace('\n', '\n  '))]
                        continue
                else:
                    input = ['.. error::\n ::\n\n  %s\n\n' % str(inst).replace('\n', '\n  ')]
                raise inst
            break
        visitor = NodeVisitor()
        walkabout(docutils_tree, visitor)
        return visitor.tree()

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory,
                          Type('text/x-rst'), type_moin_document)
default_registry.register(Converter.factory,
                          Type('x-moin/format;name=rst'), type_moin_document)
