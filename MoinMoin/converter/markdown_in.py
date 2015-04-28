# Copyright: 2008-2010 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Markdown input converter

http://daringfireball.net/projects/markdown/
"""


from __future__ import absolute_import, division

import re
import htmlentitydefs
from collections import deque

from MoinMoin.util.tree import moin_page, xml, html, xlink, xinclude
from ._util import allowed_uri_scheme, decode_data
from MoinMoin.util.iri import Iri
from MoinMoin.converter.html_in import Converter as HTML_IN_Converter

from emeraldtree import ElementTree as ET
try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from markdown import Markdown
import markdown.util as md_util
from MoinMoin import log
logging = log.getLogger(__name__)


html_in_converter = HTML_IN_Converter()
block_elements = 'p h blockcode ol ul pre address blockquote dl div fieldset form hr noscript table'.split()
BLOCK_ELEMENTS = {moin_page(x) for x in block_elements}


def postproc_text(markdown, text):
    """
    Removes HTML or XML character references and entities from a text string.

    :param text: The HTML (or XML) source text.
    :returns: The plain text, as a Unicode string, if necessary.
    """

    # http://effbot.org/zone/re-sub.htm#unescape-html

    if text is None:
        return None

    for pp in markdown.postprocessors.values():
        text = pp.run(text)

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub("&#?\w+;", fixup, text)


class Converter(object):
    # {{{ html conversion

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags = set(['div', 'p', 'strong', 'code', 'quote', 'blockquote'])

    # HTML tags to define a list, except dl which is a little bit different
    list_tags = set(['ul', 'ol'])

    # HTML tags which can be convert without attributes in a different DOM tag
    simple_tags = {  # Emphasis
        'em': moin_page.emphasis,
        'i': moin_page.emphasis,
        # Strong
        'b': moin_page.strong,
        'strong': moin_page.strong,
        # Code and Blockcode
        'pre': moin_page.blockcode,
        'tt': moin_page.code,
        'samp': moin_page.code,
        # Lists
        'dl': moin_page.list_item,
        'dt': moin_page.list_item_label,
        'dd': moin_page.list_item_body,
        # Table - th and td require special processing for alignment of cell contents
        'table': moin_page.table,
        'thead': moin_page.table_header,
        'tbody': moin_page.table_body,
        'tr': moin_page.table_row,
    }

    # HTML Tag which does not have equivalence in the DOM Tree
    # But we keep the information using <span element>
    inline_tags = set(['abbr', 'acronym', 'address', 'dfn', 'kbd'])

    # HTML tags which are completely ignored by our converter.
    # We even do not process children of these elements.
    ignored_tags = set(['applet', 'area', 'button', 'caption', 'center', 'fieldset',
                        'form', 'frame', 'frameset', 'head', 'iframe', 'input', 'isindex',
                        'label', 'legend', 'link', 'map', 'menu', 'noframes', 'noscript',
                        'optgroup', 'option', 'param', 'script', 'select', 'style',
                        'textarea', 'title', 'var',
    ])

    # standard_attributes are html attributes which are used
    # directly in the DOM tree, without any conversion
    standard_attributes = set(['title', 'class', 'style'])

    # Regular expression to detect an html heading tag
    heading_re = re.compile('h[1-6]')

    def new(self, tag, attrib, children):
        """
        Return a new element for the DOM Tree
        """
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib):
        """
        Function to copy one element to the DOM Tree.

        It first converts the child of the element,
        and the element itself.
        """
        attrib_new = self.convert_attributes(element)
        attrib.update(attrib_new)
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def new_copy_symmetric(self, element, attrib):
        """
        Create a new QName, with the same tag of the element,
        but with a different namespace.

        Then, we handle the copy normally.
        """
        tag = ET.QName(element.tag, moin_page)
        return self.new_copy(tag, element, attrib)

    def convert_attributes(self, element):
        result = {}
        for key, value in element.attrib.iteritems():
            if key in self.standard_attributes:
                result[html(key)] = value
            if key == 'id':
                result[xml('id')] = value
        return result

    def visit_heading(self, element):
        """
        Function to convert an heading tag into a proper
        element in our moin_page namespace
        """
        heading_level = element.tag[1]
        key = moin_page('outline-level')
        attrib = {}
        attrib[key] = heading_level
        return self.new_copy(moin_page.h, element, attrib)

    def visit_br(self, element):
        return moin_page.line_break()

    def visit_big(self, element):
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '120%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_small(self, element):
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '85%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_sub(self, element):
        key = moin_page('baseline-shift')
        attrib = {}
        attrib[key] = 'sub'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_sup(self, element):
        key = moin_page('baseline-shift')
        attrib = {}
        attrib[key] = 'super'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_u(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_ins(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_del(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_s(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_strike(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_hr(self, element, default_class=u'moin-hr3'):
        return self.new_copy(moin_page.separator, element, {moin_page.class_: default_class})

    def visit_img(self, element):
        """
        <img src="URI" /> --> <object xlink:href="URI />
        """
        attrib = {}
        url = Iri(element.attrib.get('src'))
        if element.attrib.get('alt'):
            attrib[html.alt] = element.attrib.get('alt')
        if url.scheme is None:
            # img tag
            target = Iri(scheme='wiki.local', path=element.attrib.get("src"), fragment=None)
            attrib[xinclude.href] = target
            new_node = xinclude.include(attrib=attrib)
        else:
            # object tag
            attrib[xlink.href] = url
            new_node = moin_page.object(attrib)
        return new_node

    def visit_object(self, element):
        """
        <object data="href"></object> --> <object xlink="href" />
        """
        key = xlink('href')
        attrib = {}
        if self.base_url:
            attrib[key] = ''.join([self.base_url, element.get(html.data)])
        else:
            attrib[key] = element.get(html.data)

        # Convert the href attribute into unicode
        attrib[key] = unicode(attrib[key])
        return moin_page.object(attrib)

    def visit_inline(self, element):
        """
        For some specific inline tags (defined in inline_tags)
        We just return <span element="tag.name">
        """
        key = html.class_
        attrib = {}
        attrib[key] = ''.join(['html-', element.tag.name])
        return self.new_copy(moin_page.span, element, attrib)

    def visit_li(self, element):
        """
        NB : A list item (<li>) is like the following snippet::

            <list-item>
                <list-item-label>label</list-item-label>
                <list-item-body>Body</list-item-body>
            </list-item>

        For <li> element, there is no label
        """
        list_item_body = ET.Element(moin_page.list_item_body,
                                    attrib={}, children=self.do_children(element))
        return ET.Element(moin_page.list_item, attrib={}, children=[list_item_body])

    def visit_list(self, element):
        """
        Convert a list of item (whatever the type : ordered or unordered)
        So we have html code like::

            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>

        Which will be converted to::

            <list>
                <list-item>
                    <list-item-body>Item 1</list-item-body>
                </list-item>
                <list-item>
                    <list-item-body>Item 2</list-item-body>
                </list-item>
            </list>
        """
        # We will define the appropriate attribute
        # according to the type of the list
        attrib = {}
        if element.tag == "ul" or element.tag == "dir":
            attrib[moin_page('item-label-generate')] = 'unordered'
        elif element.tag == "ol":
            attrib[moin_page('item-label-generate')] = 'ordered'

        return ET.Element(moin_page.list, attrib=attrib, children=self.do_children(element))

    def visit_a(self, element):
        key = xlink('href')
        attrib = {}
        href = postproc_text(self.markdown, element.attrib.get("href"))
        if allowed_uri_scheme(href):
            attrib[key] = href
        else:
            return href
        return self.new_copy(moin_page.a, element, attrib)

    def convert_align_to_class(self, attrib):
        attr = {}
        alignment = attrib.get('align')
        if alignment in (u'right', u'center', u'left'):
            attr[moin_page.class_] = alignment
        return attr

    def visit_th(self, element):
        attrib = self.convert_align_to_class(element.attrib)
        return self.new_copy(html.th, element, attrib=attrib)

    def visit_td(self, element):
        attrib = self.convert_align_to_class(element.attrib)
        return self.new_copy(html.td, element, attrib=attrib)

    def visit(self, element):
        # Our element can be converted directly, just by changing the namespace
        if element.tag in self.symmetric_tags:
            return self.new_copy_symmetric(element, attrib={})

        # Our element is enough simple to just change the tag name
        if element.tag in self.simple_tags:
            return self.new_copy(self.simple_tags[element.tag], element, attrib={})

        # Our element defines a list
        if element.tag in self.list_tags:
            return self.visit_list(element)

        # We convert our element as a span tag with element attribute
        if element.tag in self.inline_tags:
            return self.visit_inline(element)

        # We have a heading tag
        if self.heading_re.match(element.tag):
            return self.visit_heading(element)

        # Otherwise we need a specific procedure to handle it
        method_name = 'visit_' + element.tag
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # We should ignore this tag
        if element.tag in self.ignored_tags:
            logging.info("INFO : Ignored tag : {0}".format(element.tag))
            return

        logging.info("INFO : Unhandled tag : {0}".format(element.tag))
        return

    def do_children(self, element, add_lineno=False):
        new = []
        # markdown parser surrounds child nodes with unwanted u"\n" children, here we remove leading \n
        if hasattr(element, "text") and element.text is not None and element.text != u'\n':
            new.append(postproc_text(self.markdown, element.text))

        for child in element:
            r = self.visit(child)
            if r is None:
                r = ()
            elif not isinstance(r, (list, tuple)):
                if add_lineno and self.line_numbers:
                    r.attrib[html.data_lineno] = self.line_numbers.popleft()
                r = (r, )
            new.extend(r)
            # markdown parser surrounds child nodes with unwanted u"\n" children, here we drop trailing \n
            if hasattr(child, "tail") and child.tail is not None and child.tail != u'\n':
                new.append(postproc_text(self.markdown, child.tail))
        return new

    # }}}

    def count_lines(self, text):
        """
        Create a list of line numbers corresponding to the first line of each markdown block.

        The markdown parser does not provide text line numbers nor is there an easy way to
        add line numbers. As an alternative, we try to split the input text into the same blocks
        as the parser does, then calculate the starting line number of each block.  The list will be
        processed by the do_children method above.

        This method has unresolved problems caused by splitting the text into blocks based upon
        the presence of 2 adjacent line end characters, including:

            * blank lines within lists create separate blocks
            * omitting a blank line after a heading combines 2 elements into one block
            * using more than one blank lines between blocks

        The net result is we either have too few or too many line numbers in the generated list which
        will cause the double-click-to-edit autoscroll textarea to sometimes be off by several lines.

        TODO: revisit this when the parsing errors documented in contrib/serialized/items.moin
        (markdown item) are fixed.
        """
        line_numbers = deque()
        lineno = 1
        in_blockquote = False
        blocks = text.split(u'\n\n')
        for block in blocks:
            if not block:
                # bump count because empty blocks will be discarded
                lineno += 2
                continue
            line_count = block.count(u'\n')

            # detect and fix the problem of interspersed blank lines within blockquotes
            if block.startswith(u'    ') or block.startswith(u'\n    '):
                if in_blockquote:
                    lineno += line_count + 2
                    continue
                in_blockquote = True
            else:
                in_blockquote = False

            if block.startswith(u'\n'):
                lineno += 1
                line_numbers.append(lineno)
                lineno += line_count + 2 - 1  # -1 is already in count
            else:
                line_numbers.append(lineno)
                lineno += line_count + 2
        self.line_numbers = line_numbers

    def embedded_markup(self, text):
        """
        Per http://meta.stackexchange.com/questions/1777/what-html-tags-are-allowed-on-stack-exchange-sites
        markdown markup allows users to specify several "safe" HTML tags within a document. These tags include:

            a b blockquote code del dd dl dt em h1 h2 h3 i img kbd li ol p pre s sup sub strong strike ul br hr

        In addition, some markdown extensions output raw HTML tags (e.g. fenced outputs "<pre><code>...").
        To prevent the <, > characters from being escaped, the embedded tags are converted to nodes by using
        the converter in html_in.py.
        """
        try:
            # work around a possible bug - there is a traceback if HTML document has no tags
            p_text = html_in_converter(u'<p>%s</p>' % text)
        except AssertionError:
            # html_in converter (EmeraldTree) throws exceptions on markup style links: "Some text <http://moinmo.in> more text"
            p_text = text

        if not isinstance(p_text, unicode) and p_text.tag == moin_page.page and p_text[0].tag == moin_page.body and p_text[0][0].tag == moin_page.p:
            # will fix possible problem of P node having block children later
            return p_text[0][0]
        return p_text

    def convert_embedded_markup(self, node):
        """
        Recurse through tree looking for embedded markup.

        :param node: a tree node
        """
        for idx, child in enumerate(node):
            if isinstance(child, unicode):
                if u'<' in child:
                    node[idx] = self.embedded_markup(child)  # child is immutable string, so must do node[idx]
            else:
                # do not convert markup within a <pre> tag
                if not child.tag == moin_page.blockcode:
                    self.convert_embedded_markup(child)

    def convert_invalid_p_nodes(self, node):
        """
        Processing embedded HTML tags within markup or output from extensions with embedded markup can
        result in invalid HTML output caused by <p> tags enclosing a block element.

        The solution is to search for these occurances and change the <p> tag to a <div>.

        :param node: a tree node
        """
        for child in node:
            if not isinstance(child, unicode):
                if child.tag == moin_page.p and len(child):
                    for grandchild in child:
                        if not isinstance(grandchild, unicode) and grandchild.tag in BLOCK_ELEMENTS:
                            child.tag = moin_page.div
                self.convert_invalid_p_nodes(child)

    def __init__(self):
        self.markdown = Markdown(extensions=['extra', 'toc', ])

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)

        # {{{ stolen from Markdown.convert

        # Fixup the source text
        try:
            text = unicode(text)
        except UnicodeDecodeError, e:
            # Customise error message while maintaining original traceback
            e.reason += '. -- Note: Markdown only accepts unicode input!'
            raise

        text = text.replace(md_util.STX, "").replace(md_util.ETX, "")
        text = text.replace("\r\n", "\n").replace("\r", "\n") + "\n\n"
        text = text.expandtabs(self.markdown.tab_length)
        text = re.sub(r'(?<=\n) +\n', '\n', text)
        self.count_lines(text)

        # Split into lines and run the line preprocessors.
        lines = text.split("\n")
        for prep in self.markdown.preprocessors.values():
            lines = prep.run(lines)

        # Parse the high-level elements.
        md_root = self.markdown.parser.parseDocument(lines).getroot()

        # Run the tree-processors
        for treeprocessor in self.markdown.treeprocessors.values():
            new_md_root = treeprocessor.run(md_root)
            if new_md_root:
                md_root = new_md_root

        # }}}

        # md_root is a list of plain old Python ElementTree objects.

        add_lineno = bool(flaskg and flaskg.add_lineno_attr)
        converted = self.do_children(md_root, add_lineno=add_lineno)
        body = moin_page.body(children=converted)
        root = moin_page.page(children=[body])
        self.convert_embedded_markup(root)
        self.convert_invalid_p_nodes(root)

        return root

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type("text/x-markdown"), type_moin_document)
default_registry.register(Converter._factory, Type('x-moin/format;name=markdown'), type_moin_document)

# vim: foldmethod=marker
