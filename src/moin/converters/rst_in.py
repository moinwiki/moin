# Copyright: Docutils:David Goodger <goodger@python.org>
# Copyright: 2004 Matthew Gilbert <gilbert AT voxmea DOT net>
# Copyright: 2004 Alexander Schremmer <alex AT alexanderweb DOT de>
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - reStructuredText input converter.

It's based on the Docutils reST parser.
Conversion of the Docutils document tree to the MoinMoin document tree.

This converter is based on ReStructuredText (2006-09-22).
Works with Docutils version 0.5 (2008-06-25) or higher.
"""

import re

import docutils
from docutils import core, nodes, transforms, utils
from docutils.nodes import reference, literal_block
from docutils.parsers.rst import directives, roles

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from moin.constants.misc import URI_SCHEMES
from moin.utils.iri import Iri
from moin.utils.tree import html, moin_page, xlink, xinclude
from moin.utils.mime import Type, type_moin_document
from moin.wikiutil import anchor_name_from_text

from . import default_registry
from ._util import decode_data, normalize_split_text

from moin import log

logging = log.getLogger(__name__)


class NodeVisitor:
    """
    Part of docutils which converts docutils DOM tree to Moin DOM tree
    """

    def __init__(self):
        self.current_node = moin_page.body()
        self.root = moin_page.page(children=(self.current_node,))
        self.path = [self.root, self.current_node]
        self.header_size = 1
        self.status = ["document"]
        self.footnotes = dict()
        self.last_lineno = 0
        self.current_lineno = 0

    def dispatch_visit(self, node):
        """
        Call self."``visit_`` + node class name" with `node` as
        parameter.  If the ``visit_...`` method does not exist, call
        self.unknown_visit.
        """
        node_name = node.__class__.__name__
        method = getattr(self, "visit_" + node_name, self.unknown_visit)
        if isinstance(node.line, int):
            self.current_lineno = node.line
        return method(node)

    def dispatch_departure(self, node):
        """
        Call self."``depart_`` + node class name" with `node` as
        parameter.  If the ``depart_...`` method does not exist, call
        self.unknown_departure.
        """
        node_name = node.__class__.__name__
        method = getattr(self, "depart_" + node_name, self.unknown_departure)
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

    def open_moin_page_node(self, mointree_element, node=None):
        if flaskg and getattr(flaskg, "add_lineno_attr", False):
            # add data-lineno attribute for auto-scrolling edit textarea
            if self.last_lineno < self.current_lineno:
                mointree_element.attrib[html.data_lineno] = self.current_lineno
                self.last_lineno = self.current_lineno
        if node and node["ids"]:
            # IDs are prepended in empty <span> mointree elements
            for _id in node["ids"]:
                self.open_moin_page_node(moin_page.span(attrib={moin_page.id: _id}))
                self.close_moin_page_node()
        if node and node["classes"]:
            classes = node["classes"][:]
            if mointree_element.attrib.get(html.class_, ""):
                classes.insert(0, mointree_element.attrib[html.class_])
            mointree_element.attrib[html.class_] = " ".join(classes)
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

    def visit_admonition(self, node, typ="attention"):
        # use "attention" for generic admonitions, cf.
        # http://docutils.sourceforge.net/docs/ref/rst/directives.html#generic-admonition
        self.open_moin_page_node(moin_page.admonition({moin_page.type: typ}), node)

    def depart_admonition(self, node=None):
        self.close_moin_page_node()

    # see http://docutils.sourceforge.net/docs/ref/rst/directives.html#specific-admonitions
    def visit_attention(self, node):
        self.visit_admonition(node, "attention")

    depart_attention = depart_admonition

    def visit_caution(self, node):
        self.visit_admonition(node, "caution")

    depart_caution = depart_admonition

    def visit_danger(self, node):
        self.visit_admonition(node, "danger")

    depart_danger = depart_admonition

    def visit_error(self, node):
        # this is used to process parsing errors as well as user error admonitions
        self.visit_admonition(node, "error")

    depart_error = depart_admonition

    def visit_hint(self, node):
        self.visit_admonition(node, "hint")

    depart_hint = depart_admonition

    def visit_important(self, node):
        self.visit_admonition(node, "important")

    depart_important = depart_admonition

    def visit_note(self, node):
        self.visit_admonition(node, "note")

    depart_note = depart_admonition

    def visit_tip(self, node):
        self.visit_admonition(node, "tip")

    depart_tip = depart_admonition

    def visit_warning(self, node):
        self.visit_admonition(node, "warning")

    depart_warning = depart_admonition

    def visit_address(self, node):
        self.visit_docinfo_item(node, "address")

    def depart_address(self, node):
        self.depart_docinfo_item(node)

    def visit_block_quote(self, node):
        self.open_moin_page_node(moin_page.blockquote())

    def depart_block_quote(self, node):
        self.close_moin_page_node()

    def visit_attribution(self, node):
        attrib = {html.class_: "moin-rst-attribution"}
        self.open_moin_page_node(moin_page.p(attrib=attrib), node)

    def depart_attribution(self, node):
        self.close_moin_page_node()

    def visit_bullet_list(self, node):
        self.open_moin_page_node(moin_page.list(attrib={moin_page.item_label_generate: "unordered"}), node)

    def depart_bullet_list(self, node):
        self.close_moin_page_node()

    def visit_definition(self, node):
        self.open_moin_page_node(moin_page.list_item_body())

    def depart_definition(self, node):
        self.close_moin_page_node()

    def visit_definition_list(self, node):
        self.open_moin_page_node(moin_page.list(), node)

    def depart_definition_list(self, node):
        self.close_moin_page_node()

    def visit_definition_list_item(self, node):
        self.open_moin_page_node(moin_page.list_item(), node)

    def depart_definition_list_item(self, node):
        self.close_moin_page_node()

    def visit_docinfo(self, node):
        self.open_moin_page_node(moin_page.table(attrib={html.class_: "moin-rst-fieldlist"}))
        self.open_moin_page_node(moin_page.table_body())

    def depart_docinfo(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_author(self, node):
        if isinstance(node.parent, nodes.authors):
            self.open_moin_page_node(moin_page.p(), node)
        else:
            self.visit_docinfo_item(node, "author")

    def depart_author(self, node):
        if isinstance(node.parent, nodes.authors):
            self.close_moin_page_node()
        else:
            self.depart_docinfo_item(node)

    def visit_authors(self, node):
        self.visit_docinfo_item(node, "authors")

    def depart_authors(self, node):
        self.depart_docinfo_item(node)

    def visit_caption(self, node):
        self.open_moin_page_node(moin_page.figcaption())

    def depart_caption(self, node):
        self.close_moin_page_node()

    def visit_copyright(self, node):
        self.visit_docinfo_item(node, "copyright")

    def depart_copyright(self, node):
        self.depart_docinfo_item(node)

    def visit_comment(self, node):
        """
        Create moinwiki style hidden comment rather than html style: <!-- a comment -->
        """
        attrib = {moin_page.class_: "comment dashed"}
        self.open_moin_page_node(moin_page.div(attrib=attrib))

    def depart_comment(self, node):
        self.close_moin_page_node()

    def visit_contact(self, node):
        self.visit_docinfo_item(node, "contact")

    def depart_contact(self, node):
        self.depart_docinfo_item(node)

    def visit_date(self, node):
        self.visit_docinfo_item(node, "date")

    def depart_date(self, node):
        self.depart_docinfo_item(node)

    def visit_description(self, node):
        # description of an <option_group> in an <option_list_item>
        self.open_moin_page_node(moin_page.table_cell())

    def depart_description(self, node):
        self.close_moin_page_node()

    def visit_docinfo_item(self, node, name):
        # auxiliary function, called by docinfo items
        # <address>, <author>, <authors>, <contact>, <copyright>, <date>,
        # <organization>, <revision>, <status>, and <version>,
        self.open_moin_page_node(moin_page.table_row())
        self.open_moin_page_node(moin_page.table_cell())
        self.open_moin_page_node(moin_page.strong())
        self.current_node.append(name.capitalize() + ":")  # TODO: i18n
        self.close_moin_page_node()  # </strong>
        self.close_moin_page_node()  # </table_cell>
        self.open_moin_page_node(moin_page.table_cell())

    def depart_docinfo_item(self, node):
        self.close_moin_page_node()  # </table_cell>
        self.close_moin_page_node()  # </table_row>

    def visit_emphasis(self, node):
        self.open_moin_page_node(moin_page.emphasis(), node)

    def depart_emphasis(self, node):
        self.close_moin_page_node()

    def visit_entry(self, node):
        # table cell element (<th> or <td> in HTML)
        moin_table_cell = moin_page.table_cell()
        if "morerows" in node.attributes:
            moin_table_cell.set(moin_page.number_rows_spanned, repr(int(node["morerows"]) + 1))
        if "morecols" in node.attributes:
            moin_table_cell.set(moin_page.number_columns_spanned, repr(int(node["morecols"]) + 1))
        self.open_moin_page_node(moin_table_cell, node)

    def depart_entry(self, node):
        self.close_moin_page_node()

    def visit_enumerated_list(self, node):
        enum_style = {
            "arabic": None,
            "loweralpha": "lower-alpha",
            "upperalpha": "upper-alpha",
            "lowerroman": "lower-roman",
            "upperroman": "upper-roman",
        }
        moin_list = moin_page.list(attrib={moin_page.item_label_generate: "ordered"})
        type = enum_style.get(node["enumtype"], None)
        if type:
            moin_list.set(moin_page.list_style_type, type)
        startvalue = node.get("start", 1)
        if startvalue > 1:
            moin_list.set(moin_page.list_start, str(startvalue))
        self.open_moin_page_node(moin_list, node)

    def depart_enumerated_list(self, node):
        self.close_moin_page_node()

    def visit_field(self, node):
        self.open_moin_page_node(moin_page.table_row(), node)

    def depart_field(self, node):
        self.close_moin_page_node()

    def visit_field_body(self, node):
        self.open_moin_page_node(moin_page.table_cell())

    def depart_field_body(self, node):
        self.close_moin_page_node()

    def visit_field_list(self, node):
        attrib = {html.class_: "moin-rst-fieldlist"}
        self.open_moin_page_node(moin_page.table(attrib=attrib), node)
        self.open_moin_page_node(moin_page.table_body())

    def depart_field_list(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_field_name(self, node):
        self.open_moin_page_node(moin_page.table_cell(), node)
        self.open_moin_page_node(moin_page.strong())

    def depart_field_name(self, node):
        self.current_node.append(":")
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_figure(self, node):
        self.open_moin_page_node(moin_page.figure(attrib={moin_page.class_: "moin-figure"}), node)

    def depart_figure(self, node):
        self.close_moin_page_node()

    def visit_footer(self, node):
        pass

    def depart_footer(self, node):
        pass

    def visit_footnote(self, node):
        self.status.append("footnote")

    def depart_footnote(self, node):
        self.status.pop()

    def visit_footnote_reference(self, node):
        self.open_moin_page_node(moin_page.note(attrib={moin_page.note_class: "footnote"}))
        moin_footnote = moin_page.note_body()
        self.open_moin_page_node(moin_footnote)
        self.footnotes[node.children[-1]] = moin_footnote
        node.children = []

    def depart_footnote_reference(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_header(self, node):
        pass

    def depart_header(self, node):
        pass

    def visit_image(self, node):
        """
        Processes images and other transcluded objects.
        """
        whitelist = ["width", "height", "alt"]
        attrib = {}
        for key in whitelist:
            if key in node:
                attrib[html(key)] = node[key]

        # there is no 'scale' attribute, hence absent from whitelist, handled separately
        if node.get("scale"):
            scaling_factor = int(node.get("scale")) / 100.0
            for key in ("width", "height"):
                if html(key) in attrib:
                    attrib[html(key)] = int(int(attrib[html(key)]) * scaling_factor)

        # "align" parameter is invalid in HTML5. Convert it to a class defined in userstyles.css.
        userstyles = {
            "left": "left",
            "center": "center",
            "right": "right",
            # only for inline images:
            "top": "top",
            "bottom": "bottom",
            "middle": "middle",
        }
        alignment = userstyles.get(node.get("align"))
        if alignment:
            attrib[html.class_] = alignment

        url = Iri(node["uri"])
        if url.scheme is None:
            # img
            target = Iri(scheme="wiki.local", path=node["uri"], fragment=None)
            attrib[xinclude.href] = target
            moin_image = xinclude.include(attrib=attrib)
        else:
            # obj
            moin_image = moin_page.object(attrib)
            moin_image.set(xlink.href, url)
        self.open_moin_page_node(moin_image, node)

    def depart_image(self, node):
        self.close_moin_page_node()

    def visit_inline(self, node):
        classes = node["classes"]
        moin_node = moin_page.span()
        if "ins" in classes:
            moin_node = moin_page.ins()
            classes.remove("ins")
        if "del" in classes:
            moin_node = moin_page.del_()
            classes.remove("del")
        self.open_moin_page_node(moin_node, node)

    def depart_inline(self, node):
        self.close_moin_page_node()

    def visit_label(self, node):
        if self.status[-1] == "footnote":
            self.footnote_lable = node.astext()
        node.children = []

    def depart_label(self, node):
        pass

    def visit_line(self, node):
        """| first line of a line_block"""
        self.open_moin_page_node(moin_page.line_blk())

    def depart_line(self, node):
        self.close_moin_page_node()

    def visit_line_block(self, node):
        """one or more line nodes make a line_block"""
        self.open_moin_page_node(moin_page.line_block(), node)

    def depart_line_block(self, node):
        self.close_moin_page_node()

    def visit_list_item(self, node):
        self.open_moin_page_node(moin_page.list_item(), node)
        self.open_moin_page_node(moin_page.list_item_body())

    def depart_list_item(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_literal(self, node):
        self.open_moin_page_node(moin_page.code(), node)

    def depart_literal(self, node):
        self.close_moin_page_node()

    def visit_literal_block(self, node):
        parser = node.get("parser", "")
        if parser:
            named_args = re.findall(r"(\w+)=(\w+)", parser)
            simple_args = re.findall(r"(?:\s)\w+(?:\s|$)", parser)
            args = []
            for value in simple_args:
                args.append(moin_page.argument(children=[value]))
            for name, value in named_args:
                args.append(moin_page.argument(attrib={moin_page.name: name}, children=[value]))
            arguments = moin_page.arguments(children=args)
            self.open_moin_page_node(
                moin_page.part(
                    children=[arguments],
                    attrib={moin_page.content_type: "x-moin/format;name={}".format(parser.split(" ")[0])},
                ),
                node,
            )
        else:
            self.open_moin_page_node(moin_page.blockcode(), node)

    def depart_literal_block(self, node):
        self.close_moin_page_node()

    def visit_option_list(self, node):
        attrib = {html.class_: "moin-rst-optionlist"}
        self.open_moin_page_node(moin_page.table(attrib=attrib), node)
        self.open_moin_page_node(moin_page.table_body())

    def depart_option_list(self, node):
        self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_option_list_item(self, node):
        self.open_moin_page_node(moin_page.table_row(), node)

    def depart_option_list_item(self, node):
        self.close_moin_page_node()

    def visit_option_group(self, node):
        self.open_moin_page_node(moin_page.table_cell())

    def depart_option_group(self, node):
        self.close_moin_page_node()

    def visit_option(self, node):
        self.open_moin_page_node(moin_page.span(attrib={html.class_: "kbd option"}))

    def depart_option(self, node):
        self.close_moin_page_node()
        if isinstance(node.next_node(descend=False, siblings=True), nodes.option):
            self.current_node.append(", ")

    def visit_option_argument(self, node):
        self.current_node.append(node.get("delimiter", " "))

    def depart_option_argument(self, node):
        pass

    def visit_organization(self, node):
        self.visit_docinfo_item(node, "organization")

    def depart_organization(self, node):
        self.depart_docinfo_item(node)

    def visit_paragraph(self, node):
        if self.status[-1] == "footnote":
            footnote_node = self.footnotes.get(self.footnote_lable, None)
            if footnote_node:
                # TODO: `node.astext()` ignores all markup!
                # "moin" footnotes support inline markup
                footnote_node.append(node.astext())
            raise nodes.SkipNode
        self.open_moin_page_node(moin_page.p(), node)

    def depart_paragraph(self, node):
        if self.status[-1] != "footnote":
            self.close_moin_page_node()

    def visit_problematic(self, node):
        if node.hasattr("refid"):
            refuri = f"#{node['refid']}"
            attrib = {xlink.href: refuri, html.class_: "red"}
            self.open_moin_page_node(moin_page.a(attrib=attrib), node)
        else:
            self.open_moin_page_node(moin_page.span(attrib={html.class_: "red"}))

    def depart_problematic(self, node):
        self.close_moin_page_node()

    def visit_reference(self, node):
        refuri = node.get("refuri", "")
        if refuri.startswith("<<") and refuri.endswith(">>"):  # moin macro
            macro_name = refuri[2:-2].split("(")[0]
            if macro_name == "TableOfContents":
                arguments = refuri[2:-2].split("(")[1][:-1].split(",")
                moin_toc = moin_page.table_of_content()
                self.open_moin_page_node(moin_toc)
                if arguments and arguments[0]:
                    moin_toc.set(moin_page.outline_level, arguments[0])
                return
            if macro_name == "Include":
                # include macros are expanded by include.py similar to transclusions
                # rst include handles only wiki pages and does not support additional arguments like moinwiki
                arguments = refuri[2:-2].split("(")[1][:-1].split(",")
                link = Iri(scheme="wiki.local", path=arguments)
                moin_node = xinclude.include(
                    attrib={
                        xinclude.href: link,
                        moin_page.alt: refuri,
                        moin_page.content_type: "x-moin/macro;name=" + macro_name,
                    }
                )
                self.open_moin_page_node(moin_node)
                return
            try:
                arguments = refuri[2:-2].split("(")[1][:-1]
            except IndexError:
                arguments = ""  # <<DateTime>>

            self.open_moin_page_node(
                moin_page.inline_part(attrib={moin_page.content_type: f"x-moin/macro;name={macro_name}"})
            )
            if arguments:
                self.open_moin_page_node(moin_page.arguments())
                self.open_moin_page_node(arguments)
                self.close_moin_page_node()
                self.close_moin_page_node()
            return

        if refuri == "" and "refid" in node:
            # internal cross-links
            refid = node["refid"]
            target_node = node.document.ids[refid]
            # "refid" works fine with explicit anchors but the IDs given to
            # section headings use the normalization function from Moin, not Docutils.
            if isinstance(target_node, nodes.section):
                title = target_node[0]
                refid = anchor_name_from_text(title.astext())
            iri = Iri(scheme="wiki.local", fragment=refid)
        elif refuri.startswith("http") and "://" not in refuri:
            # convert links like "http:Home" to wiki-internal references
            iri = Iri("wiki.local:" + refuri.split(":", maxsplit=1)[1])
        else:
            # ensure a safe scheme, fall back to wiki-internal reference
            iri = Iri(refuri)
            if iri.scheme not in URI_SCHEMES:
                iri = Iri("wiki.local:" + refuri)
        self.open_moin_page_node(moin_page.a(attrib={xlink.href: iri}))

    def depart_reference(self, node):
        self.close_moin_page_node()

    def visit_revision(self, node):
        self.visit_docinfo_item(node, "revision")

    def depart_revision(self, node):
        self.depart_docinfo_item(node)

    def visit_row(self, node):
        self.open_moin_page_node(moin_page.table_row(), node)

    def depart_row(self, node):
        self.close_moin_page_node()

    def visit_rubric(self, node):
        self.open_moin_page_node(moin_page.p(attrib={html.class_: "moin-title moin-rubric"}))

    def depart_rubric(self, node):
        self.close_moin_page_node()

    def visit_status(self, node):
        self.visit_docinfo_item(node, "status")

    def depart_status(self, node):
        self.depart_docinfo_item(node)

    def visit_substitution_definition(self, node):
        """
        All substitutions have been made by docutils rst parser, so no need to put anything on DOM.
        Input was similar to:

        .. |a| macro:: <<Date()>>
        """
        node.children = []

    def depart_substitution_definition(self, node):
        pass

    def visit_section(self, node):
        self.header_size += 1

    def depart_section(self, node):
        self.header_size -= 1

    def visit_sidebar(self, node):
        # Sidebars typically “float” to the side of the page.
        self.open_moin_page_node(moin_page.div(attrib={html.class_: "moin-aside moin-sidebar"}))

    def depart_sidebar(self, node):
        self.close_moin_page_node()

    def visit_strong(self, node):
        self.open_moin_page_node(moin_page.strong(), node)

    def depart_strong(self, node):
        self.close_moin_page_node()

    def visit_subscript(self, node):
        self.open_moin_page_node(moin_page.span(attrib={moin_page.baseline_shift: "sub"}), node)

    def depart_subscript(self, node):
        self.close_moin_page_node()

    def visit_subtitle(self, node):
        # subtitle of a page, section, or sidebar
        # TODO: Use a <hgroup> in HTML?
        self.open_moin_page_node(moin_page.p(attrib={html.class_: "moin-subheading"}))

    def depart_subtitle(self, node):
        self.close_moin_page_node()

    def visit_superscript(self, node):
        self.open_moin_page_node(moin_page.span(attrib={moin_page.baseline_shift: "super"}), node)

    def depart_superscript(self, node):
        self.close_moin_page_node()

    def visit_system_message(self, node):
        # an element reporting a parsing issue (DEBUG, INFO, WARNING, ERROR, or SEVERE)
        if node.get("level", 4) < 3:
            self.visit_admonition(node, "caution")
        else:
            self.visit_admonition(node, "error")
        self.open_moin_page_node(moin_page.p(attrib={html.class_: "moin-title"}))
        title = f"{node['type']}/{node['level']}"
        self.current_node.append(f"System Message: {title}")
        if node.hasattr("line"):
            self.current_node.append(f" ({node['source']} line {node['line']}) ")
        if node.get("backrefs", []):
            backrefuri = f"#{node['backrefs'][0]}"
            self.open_moin_page_node(moin_page.a(attrib={xlink.href: backrefuri}), node)
            self.current_node.append("backlink")
            self.close_moin_page_node()  # </a>
        self.close_moin_page_node()  # </p>

    def depart_system_message(self, node):
        self.depart_admonition(node)

    def visit_table(self, node):
        self.open_moin_page_node(moin_page.table(), node)

    def depart_table(self, node):
        self.close_moin_page_node()

    def visit_tbody(self, node):
        self.open_moin_page_node(moin_page.table_body())

    def depart_tbody(self, node):
        self.close_moin_page_node()

    def visit_target(self, node):
        """
        Pass explicit anchor as SPAN with ID attribute

        .. _example:

        Paragraph with _`inline target`.
        """
        if "refuri" in node or "refid" in node or "refname" in node:
            return  # already handled by Docutils "transforms"
        moin_target = moin_page.span()
        if node["ids"]:
            moin_target.attrib[moin_page.id] = node["ids"][0]
        self.open_moin_page_node(moin_target)

    def depart_target(self, node):
        if "refuri" in node or "refid" in node or "refname" in node:
            return  # already handled by Docutils "transforms"
        self.close_moin_page_node()

    def visit_term(self, node):
        self.open_moin_page_node(moin_page.list_item_label())

    def depart_term(self, node):
        # classifiers arrive as siblings of the term; search the parent and convert them to children
        for child in node.parent:
            if isinstance(child, docutils.nodes.classifier):
                classifier = ":" + child[0]
                self.open_moin_page_node(moin_page.span(children=[classifier]))
                self.close_moin_page_node()
        self.close_moin_page_node()

    def visit_tgroup(self, node):
        """
        The tgroup node is presented as the parent of thead and tbody. These should be siblings.
        Other children are colspec which have a colwidth attribute. Using these numbers to specify
        a width on the col element similar to Sphinx results in an HTML validation error.
        There is no markup to specify styling such as background color.
        """
        # TODO: convert collumn width values into a form understood by Moin.
        pass

    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        self.open_moin_page_node(moin_page.table_header())

    def depart_thead(self, node):
        self.close_moin_page_node()

    def visit_title(self, node):
        # <title> is used in <admonition>, <document>, <section>, <sidebar>, <table>, and <topic>
        # TODO: table title is currently ignored!
        if isinstance(node.parent, (nodes.admonition, nodes.sidebar, nodes.topic)):
            # informal title: don't include in ToC, no section numbering
            self.open_moin_page_node(moin_page.p(attrib={html.class_: "moin-title"}))
        else:
            self.open_moin_page_node(moin_page.h(attrib={moin_page.outline_level: repr(self.header_size)}))

    def depart_title(self, node):
        self.close_moin_page_node()

    def visit_topic(self, node):
        # content that is separate from the flow of the document
        self.open_moin_page_node(moin_page.div(attrib={html.class_: "moin-aside"}))

    def depart_topic(self, node):
        self.close_moin_page_node()

    def visit_title_reference(self, node):
        pass

    def depart_title_reference(self, node):
        pass

    def visit_transition(self, node, default_class="moin-hr3"):
        # TODO: add to rst_out
        attrib = {html.class_: default_class}
        self.open_moin_page_node(moin_page.separator(attrib=attrib), node)

    def depart_transition(self, node):
        self.close_moin_page_node()

    def visit_version(self, node):
        self.visit_docinfo_item(node, "version")

    def depart_version(self, node):
        self.depart_docinfo_item(node)

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


class Parser(docutils.parsers.rst.Parser):
    """reStructuredText parser for the MoinMoin wiki.

    Registers a "transform__" for hyperlink references
    without matching target__.

    Also register the "transforms" that are added by default for a Docutils writer.

    __ https://docutils.sourceforge.io/docs/api/transforms.html
    __ https://docutils.sourceforge.io/docs/ref/doctree.html#target
    """

    # Use class values matching the pre-defined CSS highlight rules
    settings_default_overrides = {"syntax_highlight": "short"}

    config_section = "MoinMoin parser"
    config_section_dependencies = ("parsers", "restructuredtext parser")

    def get_transforms(self):
        """Add WikiReferences to the registered transforms."""
        moin_parser_transforms = [
            WikiReferences,
            transforms.universal.StripClassesAndElements,
            transforms.universal.Messages,
            transforms.universal.FilterMessages,
        ]
        return super().get_transforms() + moin_parser_transforms


class WikiReferences(transforms.Transform):
    """Resolve references without matching target as local wiki references.

    Set the "refuri" attribute to the whitespace-normalized (but NOT case
    normalized) link text (`visit_reference()` adds the "wiki.local" scheme.)

    Cf. https://docutils.sourceforge.io/docs/api/transforms.html.
    """

    default_priority = 775
    # Apply between `InternalTargets` (660) and `DanglingReferences` (850)

    def apply(self) -> None:
        for node in self.document.findall(nodes.reference):
            # Skip resolved references, unresolvable references,
            # and references with matching target:
            if node.resolved or "refname" not in node or self.document.nameids.get(node["refname"]):
                continue
            # Get the refuri from the link text (keep case)
            refuri = nodes.whitespace_normalize_name(node.astext())
            # Skip references whose "refname" attribute differs from the
            # refuri by more than case:
            if node["refname"] != refuri.lower():
                continue
            node["refuri"] = refuri
            # Mark as resolved:
            del node["refname"]
            node.resolved = True


class MoinDirectives:
    """
    Class to handle all custom directive handling. This code is called as
    part of the parsing stage.
    """

    def __init__(self):

        # include MoinMoin pages
        directives.register_directive("include", self.include)

        # used for MoinMoin macros
        directives.register_directive("macro", self.macro)

        # used for MoinMoin tables of content
        directives.register_directive("contents", self.table_of_content)

        # used for MoinMoin parsers
        directives.register_directive("parser", self.parser)

        # disallow a few directives in order to prevent XSS
        # for directive in ('meta', 'include', 'raw'):
        for directive in ("meta", "raw"):
            directives.register_directive(directive, None)

        # disable the raw role
        roles._roles["raw"] = None

        # As a quick fix for infinite includes we only allow a fixed number of
        # includes per page
        self.num_includes = 0
        self.max_includes = 10

    # Handle the include directive rather than letting the default docutils
    # parser handle it. This allows the inclusion of MoinMoin pages instead of
    # something from the filesystem.
    def include(self, name, arguments, options, content, lineno, content_offset, block_text, state, state_machine):
        # content contains the included file name

        # TODO: i18n for errors

        # Limit the number of documents that can be included
        if self.num_includes < self.max_includes:
            self.num_includes += 1
        else:
            lines = ["**Maximum number of allowed includes exceeded**"]
            state_machine.insert_input(lines, "MoinDirectives")
            return []

        if content:
            macro = f"<<Include({content[0]})>>"
        else:
            macro = "<<Include()>>"
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
    def macro(self, name, arguments, options, content, lineno, content_offset, block_text, state, state_machine):
        # .. macro:: <<DateTime()>>
        # content contains macro to be called
        if len(content):
            # Allow either with or without brackets
            if content[0].startswith("<<"):
                macro = content[0]
            else:
                macro = f"<<{content[0]}>>"
            ref = reference(macro, refuri=macro)
            ref["name"] = macro
            return [ref]
        return

    macro.has_content = macro.content = True
    macro.option_spec = {}
    macro.required_arguments = 1
    macro.optional_arguments = 0

    def table_of_content(
        self, name, arguments, options, content, lineno, content_offset, block_text, state, state_machine
    ):
        text = ""
        for i in content:
            m = re.search(r":(\w+): (\w+)", i)
            if m and len(m.groups()) == 2:
                if m.groups()[0] == "depth":
                    text = m.groups()[1]
        macro = f"<<TableOfContents({text})>>"
        ref = reference(macro, refuri=macro)
        ref["name"] = macro
        return [ref]

    table_of_content.has_content = table_of_content.content = True
    table_of_content.option_spec = {}
    table_of_content.required_arguments = 1
    table_of_content.optional_arguments = 0

    def parser(self, name, arguments, options, content, lineo, content_offset, block_text, state, state_machine):
        block = literal_block()
        block["parser"] = content[0]
        block.children = [nodes.Text("\n".join(content[1:]))]
        return [block]

    parser.has_content = parser.content = True
    parser.option_spec = {}
    parser.required_arguments = 1
    parser.optional_arguments = 0


class Converter:
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        input = normalize_split_text(text)
        MoinDirectives()
        while True:
            input = "\n".join(input)
            try:
                docutils_tree = core.publish_doctree(source=input, source_path="rST input", parser=Parser())
            except utils.SystemMessage as inst:
                string_numb = re.match(
                    re.compile(r"<string>:([0-9]*):\s*\(.*?\)\s*(.*)", re.X | re.U | re.M | re.S), str(inst)
                )
                if string_numb:
                    str_num = string_numb.group(1)
                    input = input.split("\n")
                    if str_num:
                        input = [
                            (
                                ".. error::\n"
                                " ::\n"
                                "\n"
                                "  Parse error on line number {}:\n"
                                "\n"
                                "  {}\n"
                                "\n"
                                "  Go back and try to fix that.\n"
                                "\n"
                            ).format(str_num, string_numb.group(2).replace("\n", "\n  "))
                        ]
                        continue
                else:
                    input = [".. error::\n ::\n\n  {}\n\n".format(str(inst).replace("\n", "\n  "))]
                raise inst
            break
        visitor = NodeVisitor()
        walkabout(docutils_tree, visitor)
        ret = visitor.tree()
        return ret


default_registry.register(Converter.factory, Type("text/x-rst"), type_moin_document)
default_registry.register(Converter.factory, Type("x-moin/format;name=rst"), type_moin_document)
