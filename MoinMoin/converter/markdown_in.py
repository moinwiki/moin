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

from MoinMoin.util.tree import moin_page, xml, html, xlink
from ._util import allowed_uri_scheme, decode_data

from MoinMoin import log
logging = log.getLogger(__name__)

from emeraldtree import ElementTree as ET

from markdown import Markdown
import markdown.util as md_util

def postproc_text(markdown, text):
    """
    Removes HTML or XML character references and entities from a text string.

    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
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
        return text # leave as is

    return re.sub("&#?\w+;", fixup, text)

class Converter(object):
    # {{{ html conversion

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags = set(['div', 'p', 'strong', 'code', 'quote', 'blockquote'])

    # HTML tags to define a list, except dl which is a little bit different
    list_tags = set(['ul', 'dir', 'ol'])

    # HTML tags which can be convert without attributes in a different DOM tag
    simple_tags = {# Emphasis
                   'em': moin_page.emphasis, 'i': moin_page.emphasis,
                   # Strong
                   'b': moin_page.strong, 'strong': moin_page.strong,
                   # Code and Blockcode
                   'pre': moin_page.blockcode, 'tt': moin_page.code,
                   'samp': moin_page.code,
                   # Lists
                   'dt': moin_page.list_item_label, 'dd': moin_page.list_item_body,
                   # TODO : Some tags related to tables can be also simplify
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

    def visit_hr(self, element, min_class=u'moin-hr1', max_class=u'moin-hr6', default_class=u'moin-hr3'):
        hr_class = element.attrib.get('class')
        if not (min_class <= hr_class <= max_class):
            element.attrib[html('class')] = default_class
        return self.new_copy(moin_page.separator, element, {})

    def visit_img(self, element):
        """
        <img src="URI" /> --> <object xlink:href="URI />
        """
        key = xlink('href')
        attrib = {}
        attrib[key] = element.attrib.get("src")
        return moin_page.object(attrib)

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
        key = html('class')
        attrib = {}
        attrib[key] = ''.join(['html-', element.tag.name])
        return self.new_copy(moin_page.span, element, attrib)

    def visit_li(self, element):
        """
        NB : A list item (<li>) is like the following snippet :
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
        So we have a html code like :
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>

        Which will be convert like :
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

        return ET.Element(moin_page.list, attrib=attrib,
                children=self.do_children(element))

    def visit_a(self, element):
        key = xlink('href')
        attrib = {}
        href = postproc_text(self.markdown, element.attrib.get("href"))
        if allowed_uri_scheme(href):
            attrib[key] = href
        else:
            return href
        return self.new_copy(moin_page.a, element, attrib)

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

    def do_children(self, element):
        new = []
        if hasattr(element, "text") and element.text is not None:
            new.append(postproc_text(self.markdown, element.text))

        for child in element:
            r = self.visit(child)
            if r is None:
                r = ()
            elif not isinstance(r, (list, tuple)):
                r = (r, )
            new.extend(r)
            if hasattr(child, "tail") and child.tail is not None:
                new.append(postproc_text(self.markdown, child.tail))
        return new

    # }}}

    def __init__(self):
        self.markdown = Markdown()

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
        text = re.sub(r'\n\s+\n', '\n\n', text)
        text = text.expandtabs(8)

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

        converted = self.do_children(md_root)
        body = moin_page.body(children=converted)
        root = moin_page.page(children=[body])

        return root

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type("text/x-markdown"), type_moin_document)
default_registry.register(Converter._factory, Type('x-moin/format;name=markdown'), type_moin_document)

# vim: foldmethod=marker
