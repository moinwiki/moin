# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - HTML input converter
Converts an XHTML document into an internal document tree.

TODO : Add support for style
"""


from __future__ import absolute_import

import re

from emeraldtree import ElementTree as ET
from emeraldtree.html import HTML

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.util.tree import html, moin_page, xlink, xml

from ._wiki_macro import ConverterMacro

class Converter(object):
    """
    Converter html -> .x.moin.document
    """
    # Namespace of our input data
    html_namespace = {
        html.namespace: 'xhtml',
        }

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

    # Store the Base URL for all the URL of the document
    base_url = ''

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        """
        Function called by the converter to process the
        conversion.

        TODO: Add support for different arguments
        """
        # Be sure we have empty string in the base url
        self.base_url = ''

        # We create an element tree from the HTML content
        # The content is a list of string, line per line
        # We can concatenate all in one string
        html_str = ''
        html_str = html_str.join(content)
        html_tree = HTML(html_str)

        # We should have a root element, which will be converted as <page>
        # for the DOM Tree. It can be <html> or <div>.
        # NB : If <html> used, it will be converted back to <div> after
        # one roundtrip
        if html_tree.tag.name != 'html' and html_tree.tag.name != 'div':
            html_str = ''.join(['<div>', html_str, '</div>'])
            html_tree = HTML(html_str)

        # Start the conversion of the first element
        # Every child of each element will be recursively convert too
        element = self.do_children(html_tree)

        # Add Global element to our DOM Tree
        body = moin_page.body(children=element)
        root = moin_page.page(children=[body])
        return root

    def do_children(self, element):
        """
        Function to process the conversion of the child of
        a given elements.
        """
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                new.extend(r)
            else:
                new.append(child)
        return new

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
        tag = ET.QName(element.tag.name, moin_page)
        return self.new_copy(tag, element, attrib)

    def convert_attributes(self, element):
        result = {}
        for key, value in element.attrib.iteritems():
            if key.uri == html and \
                key.name in self.standard_attributes:
                result[key] = value
            if key.name == 'id':
                result[xml('id')] = value
        return result

    def visit(self, element):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the found namespace.
        """
        uri = element.tag.uri
        name = self.html_namespace.get(uri, None)
        if name is not None:
            method_name = 'visit_' + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)

            # We process children of the unknown element
            return self.do_children(element)

    def visit_xhtml(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the XHTML namespace.

        We will detect the name of the tag, and apply an appropriate
        procedure to convert it.
        """
        # Our element can be converted directly, just by changing the namespace
        if element.tag.name in self.symmetric_tags:
            return self.new_copy_symmetric(element, attrib={})

        # Our element is enough simple to just change the tag name
        if element.tag.name in self.simple_tags:
            return self.new_copy(self.simple_tags[element.tag.name], element, attrib={})

        # Our element define a list
        if element.tag.name in self.list_tags:
            return self.visit_xhtml_list(element)

        # We convert our element as a span tag with element attribute
        if element.tag.name in self.inline_tags:
            return self.visit_xhtml_inline(element)

        # We have an heading tag
        if self.heading_re.match(element.tag.name):
            return self.visit_xhtml_heading(element)

        # Otherwise we need a specific procedure to handle it
        method_name = 'visit_xhtml_' + element.tag.name
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # We should ignore this tag
        if element.tag.name in self.ignored_tags:
            logging.debug("WARNING : Ignored tag : %s" % element.tag.name)
            return

        # Otherwise we process children of the unknown element
        logging.debug("WARNING : Unknown tag : %s" % element.tag.name)
        return self.do_children(element)

    def visit_xhtml_base(self, element):
        """
        Function to store the base url for the relative url of the document
        """
        self.base_url = element.get(html.href)

    def visit_xhtml_heading(self, element):
        """
        Function to convert an heading tag into the proper
        element in our moin_page namespace
        """
        heading_level = element.tag.name[1]
        key = moin_page('outline-level')
        attrib = {}
        attrib[key] = heading_level
        return self.new_copy(moin_page.h, element, attrib)

    def visit_xhtml_br(self, element):
        """
        <br /> --> <line-break />
        """
        return moin_page.line_break()

    def visit_xhtml_big(self, element):
        """
        <big>Text</big> --> <span font-size=120%>Text</span>
        """
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '120%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_small(self, element):
        """
        <small>Text</small> --> <span font-size=85%>Text</span>
        """
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '85%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sub(self, element):
        """
        <sub>Text</sub> --> <span base-line-shift="sub">Text</span>
        """
        key = moin_page('baseline-shift')
        attrib = {}
        attrib[key] = 'sub'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sup(self, element):
        """
        <sup>Text</sup> --> <span base-line-shift="super">Text</span>
        """
        key = moin_page('baseline-shift')
        attrib = {}
        attrib[key] = 'super'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_u(self, element):
        """

        <u>Text</u> --> <span text-decoration="underline">Text</span>
        """
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_ins(self, element):
        """
        <ins>Text</ins> --> <span text-decoration="underline">Text</span>
        """
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_del(self, element):
        """
        <del>Text</del> --> <span text-decoration="underline">Text</span>
        """
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_s(self, element):
        """
        <s>Text</s> --> <span text-decoration="line-through">Text</span>
        """
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_strike(self, element):
        """
        <strike>Text</strike> --> <span text-decoration="line-through">Text</span>
        """
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_hr(self, element, min_class=u'moin-hr1', max_class=u'moin-hr6', default_class=u'moin-hr3'):
        """
        <hr /> --> <separator />
        """
        hr_class = element.attrib.get(html('class'))
        if not (min_class <= hr_class <= max_class):
            element.attrib[html('class')] = default_class
        return self.new_copy(moin_page.separator, element, {})

    def visit_xhtml_a(self, element):
        """
        <a href="URI">Text</a> --> <a xlink:href="URI">Text</a>
        """
        key = xlink('href')
        attrib = {}
        if self.base_url:
            attrib[key] = ''.join([self.base_url, element.get(html.href)])
        else:
            attrib[key] = element.get(html.href)
        return self.new_copy(moin_page.a, element, attrib)

    def visit_xhtml_img(self, element):
        """
        <img src="URI" /> --> <object xlink:href="URI />
        """
        key = xlink('href')
        attrib = {}
        if self.base_url:
            attrib[key] = ''.join([self.base_url, element.get(html.src)])
        else:
            attrib[key] = element.get(html.src)
        return moin_page.object(attrib)

    def visit_xhtml_object(self, element):
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

    def visit_xhtml_inline(self, element):
        """
        For some specific inline tags (defined in inline_tags)
        We just return <span element="tag.name">
        """
        key = html('class')
        attrib = {}
        attrib[key] = ''.join(['html-', element.tag.name])
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_list(self, element):
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
        if element.tag.name == "ul" or element.tag.name == "dir":
            attrib[moin_page('item-label-generate')] = 'unordered'
        elif element.tag.name == "ol":
            attrib[moin_page('item-label-generate')] = 'ordered'

            # We check which kind of style we have
            style = element.get(html.type)
            if 'A' == style:
                attrib[moin_page('list-style-type')] = 'upper-alpha'
            elif 'I' == style:
                attrib[moin_page('list-style-type')] = 'upper-roman'
            elif 'a' == style:
                attrib[moin_page('list-style-type')] = 'lower-alpha'
            elif 'i' == style:
                attrib[moin_page('list-style-type')] = 'lower-roman'

        # we should not have any strings in the child
        list_items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                list_items.extend(r)
        return ET.Element(moin_page.list, attrib=attrib, children=list_items)

    def visit_xhtml_dl(self, element):
        """
        Convert a list of definition. The conversion is like :
        <dl>
            <dt>Label 1</dt><dd>Text 1</dd>
            <dt>Label 2</dt><dd>Text 2</dd>
        </dl>

        will give

        <list>
            <list-item>
                <list-item-label>Label 1</list-item-label>
                <list-item-body>Text 1</list-item-body>
            </list-item>
            <list-item>
                <list-item-label>Label 2</list-item-label>
                <list-item-body>Text 2</list-item-body>
            </list-item>
        </list>
        """
        list_item = []
        pair = []
        number_pair = 0
        # We will browse the child, and try to catch all the pair
        # of <dt><dd>
        for child in element:
            # We need one dt tag, and one dd tag, a have a pair
            if (child.tag.name == 'dt' or child.tag.name == 'dd'):
                number_pair = number_pair + 1

            # The following code is similar to do_children method
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                pair.extend(r)
            else:
                pair.append(r)

            if (number_pair == 2):
                # We have two elements of the pair
                # So we can put it into a <list-item> element
                list_item_element = ET.Element(moin_page.list_item,
                                               attrib={}, children=pair)
                list_item.append(list_item_element)
                pair = []
                number_pair = 0

        # we return the <list> with all the list item element
        return ET.Element(moin_page.list, attrib={}, children=list_item)

    def visit_xhtml_li(self, element):
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

    def visit_xhtml_table(self, element):
        # we should not have any strings in the child
        list_table_elements = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                list_table_elements.extend(r)
        return ET.Element(moin_page.table, attrib={}, children=list_table_elements)

    def visit_xhtml_thead(self, element):
        return self.new_copy(moin_page.table_header, element, attrib={})

    def visit_xhtml_tfoot(self, element):
        return self.new_copy(moin_page.table_footer, element, attrib={})

    def visit_xhtml_tbody(self, element):
        return self.new_copy(moin_page.table_body, element, attrib={})

    def visit_xhtml_tr(self, element):
        return self.new_copy(moin_page.table_row, element, attrib={})

    def visit_xhtml_td(self, element):
        attrib = {}
        rowspan = element.get(html.rowspan)
        colspan = element.get(html.colspan)
        if rowspan:
            attrib[moin_page('number-rows-spanned')] = rowspan
        if colspan:
            attrib[moin_page('number-columns-spanned')] = colspan
        return self.new_copy(moin_page.table_cell, element, attrib=attrib)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('text/html'), type_moin_document)
