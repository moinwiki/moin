# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: table conversion based on html_out table conversion by Bastian Blank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - DocBook output converter

Converts an internal document tree into a DocBook v5 document.
"""

from emeraldtree import ElementTree as ET

from moin.utils.tree import html, moin_page, xlink, docbook, xml
from moin.constants.contenttypes import CONTENTTYPE_NONEXISTENT
from moin.utils.mime import Type, type_moin_document

from . import default_registry, ElementException

from moin import log

logging = log.getLogger(__name__)


class Converter:
    """
    Converter application/x.moin.document -> application/docbook+xml
    """

    namespaces_visit = {moin_page: "moinpage"}

    unsupported_tags = {"separator"}

    # Only these admonitions are supported by DocBook 5
    admonition_tags = {"caution", "important", "note", "tip", "warning"}

    # DOM Tree element which can easily be converted into a DocBook
    # element, without attributes.
    simple_tags = {
        "code": docbook.literal,
        "emphasis": docbook.emphasis,
        "list-item": docbook.varlistentry,
        "list-item-label": docbook.term,
        "quote": docbook.quote,
    }

    # We store the standard attributes of an element.
    # Once we have been able to put it into an output element,
    # we clear this attribute.
    standard_attribute = {}

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, element, **kw):
        self.section_children = {}
        self.parent_section = 0
        self.current_section = 0
        self.table_counter = 0
        self.root_section = 10
        # We can define the title of the document
        # using the title keyword in the argument
        if "title" in kw:
            self.title = kw["title"]
        else:
            self.title = "Untitled"

        return self.visit(element)

    def do_children(self, element):
        """
        Function to process the conversion of the children
        of a given element.

        Return a list of elements.
        """
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                new.extend(r)
            else:
                new.append(child)
        return new

    def new(self, tag, attrib, children):
        """
        Return a new element in the DocBook tree.
        """
        if self.standard_attribute:
            attrib.update(self.standard_attribute)
            self.standard_attribute = {}
        if self.current_section > 0:
            self.section_children[self.current_section].append(ET.Element(tag, attrib=attrib, children=children))
        else:
            return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib):
        """
        Function to copy one element to the DocBook tree

        It first converts the children of the element,
        and then the element itself
        """
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def get_standard_attributes(self, element):
        """
        We will extract the standard attributes of the element, if any.
        We save the result in standard_attribute.
        """
        result = {}
        for key, value in element.attrib.items():
            if key.uri == xml:
                result[key] = value
        if result:
            # We clear standard_attribute, if ancestror attribute
            # was stored and has not been written in to the output,
            # anyway the new standard attributes will get higher priority
            self.standard_attribute = result

    def visit(self, element):
        """
        Function called at each element to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the found namespace.
        """
        uri = element.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            method_name = "visit_" + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)
        # We process children of the unknown element
        return self.do_children(element)

    def visit_moinpage(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the moin_page namespace.

        We will choose the most appropriate procedure to convert
        the element according to the tag name
        """
        # Save the standard attribute of the element
        self.get_standard_attributes(element)

        # Check if we can a simple conversion
        if element.tag.name in self.simple_tags:
            return self.visit_simple_tag(element)

        # Check that the tag is supported
        if element.tag.name in self.unsupported_tags:
            logging.warning(f"Unsupported tag : {element.tag.name}")
            return self.do_children(element)

        method_name = "visit_moinpage_" + element.tag.name.replace("-", "_")
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # Otherwise we process the children of the unknown element
        logging.warning(f"Unknown tag : {element.tag.name}")
        return self.do_children(element)

    def visit_moinpage_a(self, element):
        """
        LINK Conversion.

        Link are defined using the XLINK namespace either
        for the DOM Tree and in DocBook specification, so
        the converter can just copy each xlink: attribute
        into an <link> tag.
        """
        attrib = {}
        for key, value in element.attrib.items():
            if key.uri == xlink:
                attrib[key] = value
        return self.new_copy(docbook.link, element, attrib=attrib)

    def visit_moinpage_admonition(self, element):
        """
        There is 5 admonition in DocBook, which are also supported
        in the DOM Tree.

        For instance: <caution> --> <admonition type='caution'>
        """
        tag = element.get(moin_page("type"))
        if tag in self.admonition_tags:
            # Our tag is valid for DocBook 5
            return self.new_copy(docbook(tag), element, attrib={})
        else:
            # For the other situation, just ignore the element
            return self.do_children(element)

    def visit_moinpage_blockcode(self, element):
        """
        <blockcode>text</blockcode> --> <screen><![CDATA[text]]></scren>
        """
        code_str = "".join(element)
        children = "".join(["<![CDATA[", code_str, "]]>"])
        return self.new(docbook.screen, attrib={}, children=children)

    def visit_moinpage_blockquote(self, element):
        """
        Convert::

            <blockquote>text<blockquote>

        to::

            <blockquote>
                <attribution>Unknown</attribution>
                <simpara>text</text>
            </blockquote>

        Expand::

        <blockquote source="author">text</blockquote>

        output::

            <blockquote>
                <attribution>author</attribution>
                <simpara>text</text>
            </blockquote>
        """
        author = element.get(moin_page("source"))
        if not author:
            # TODO: Internationalization
            author = "Unknown"
        attribution = self.new(docbook("attribution"), attrib={}, children=[author])
        children = self.do_children(element)
        para = self.new(docbook("simpara"), attrib={}, children=children)
        return self.new(docbook("blockquote"), attrib={}, children=[attribution, para])

    def visit_moinpage_h(self, element):
        """
        There is not really heading in DocBook, but rather section with
        title. The section is a root tag for all the elements which in
        the dom tree will be between two heading tags.

        So we need to process child manually to determine correctly the
        children of each section.

        A section is closed when we have a new heading with an equal or
        higher level.
        """
        depth = element.get(moin_page("outline-level"), 1)
        try:
            depth = int(depth)
        except ValueError:
            raise ElementException("page:outline-level needs to be an integer")
        # We will have a new section
        # under another section
        if depth > self.current_section:
            self.parent_section = self.current_section
            self.current_section = int(depth)
            self.section_children[self.current_section] = []
            # NB : Error with docbook.title
            title = ET.Element(docbook("title"), attrib={}, children=element[0])
            self.section_children[self.current_section].append(title)

        # We will close a section before starting a new one
        # Need more test
        elif depth < self.current_section:
            if self.parent_section != 0:
                section_tag = f"sect{self.parent_section}"
                section = ET.Element(
                    docbook(section_tag), attrib={}, children=self.section_children[self.current_section]
                )
                self.section_children[self.parent_section].append(section)
                self.current_section = int(depth)

    def visit_moinpage_line_break(self, element):
        # XXX: Not so good choice.
        return docbook.sbr()

    def visit_moinpage_list(self, element):
        """
        Function called to handle the conversion of list.

        It will called a specific function to handle (un)ordered list,
        with the appropriate DocBook tag.

        Or a specific function to handle definition list.
        """
        item_label_generate = element.get(moin_page("item-label-generate"))
        if "ordered" == item_label_generate:
            attrib = {}
            # Get the list-style-type to define correctly numeration
            list_style_type = element.get(moin_page("list-style-type"))
            if "upper-alpha" == list_style_type:
                attrib[docbook("numeration")] = "upperalpha"
            elif "upper-roman" == list_style_type:
                attrib[docbook("numeration")] = "upperroman"
            elif "lower-alpha" == list_style_type:
                attrib[docbook("numeration")] = "loweralpha"
            elif "lower-roman" == list_style_type:
                attrib[docbook("numeration")] = "lowerroman"
            else:
                attrib[docbook("numeration")] = "arabic"

            return self.handle_simple_list(docbook.orderedlist, element, attrib=attrib)
        elif "unordered" == item_label_generate:
            return self.handle_simple_list(docbook.itemizedlist, element, attrib={})
        else:
            return self.new_copy(docbook.variablelist, element, attrib={})

    def visit_moinpage_list_item_body(self, element):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                items.extend(r)
            else:
                an_item = ET.Element(docbook.simpara, attrib={}, children=child)
                items.append(an_item)
        return ET.Element(docbook.listitem, attrib={}, children=items)

    def visit_moinpage_note(self, element):
        """
        <note note-class="footnote"><note-body>text</note-body></note>
          --> <footnote><simpara>text</simpara></footnote>
        """
        note_class = element.get(moin_page("note-class"))
        # We only convert footnote, we do not convert endnote yet
        if note_class != "footnote":
            return

        # We will check the presence of a body
        body = None
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.uri == moin_page:
                    if child.tag.name == "note-body":
                        body = self.do_children(child)
        # We process note only with note-body child
        if not body:
            return

        body = self.new(docbook.simpara, attrib={}, children=body)
        return self.new(docbook.footnote, attrib={}, children=[body])

    def visit_moinpage_object(self, element):
        """
        Convert::

        <object type='image/' xlink:href='uri'/>

        to::

            <inlinemediaobject>
                  <imageobject>
                        <imagedata fileref="uri" />
                  </imageobject>
            </inlinemediaobject>

        Similar for video and audio object.
        """
        href = element.get(xlink.href, None)
        attrib = {}
        mimetype = Type(_type=element.get(moin_page.type_, CONTENTTYPE_NONEXISTENT))
        if href:
            attrib[docbook.fileref] = href
            if Type("image/").issupertype(mimetype):
                object_data = self.new(docbook.imagedata, attrib=attrib, children=[])
                object_element = self.new(docbook.imageobject, attrib={}, children=[object_data])
            elif Type("video/").issupertype(mimetype):
                object_data = self.new(docbook.videodata, attrib=attrib, children=[])
                object_element = self.new(docbook.videoobject, attrib={}, children=[object_data])
            elif Type("audio/").issupertype(mimetype):
                object_data = self.new(docbook.audiodata, attrib=attrib, children=[])
                object_element = self.new(docbook.audioobject, attrib={}, children=[object_data])
            else:
                return
        else:
            return
        return self.new(docbook.inlinemediaobject, attrib={}, children=[object_element])

    def visit_moinpage_table(self, element):
        # TODO: Attributes conversion
        title = element.get(html("title"))
        if not title:
            # TODO: Translation
            title = f"Table {self.table_counter}"
        self.table_counter += 1
        caption = ET.Element(docbook("caption"), attrib={}, children=[title])
        children = [caption]
        children.extend(self.do_children(element))
        return self.new(docbook.table, attrib={}, children=children)

    def visit_moinpage_table_body(self, element):
        # TODO: Attributes conversion
        return self.new_copy(docbook.tbody, element, attrib={})

    def visit_moinpage_table_cell(self, element):
        attrib = {}
        rowspan = element.get(moin_page("number-rows-spanned"))
        colspan = element.get(moin_page("number-columns-spanned"))
        print(f"rowspan : {rowspan}")
        if rowspan:
            attrib[docbook.rowspan] = rowspan
        if colspan:
            attrib[docbook.colspan] = colspan
        return self.new_copy(docbook.td, element, attrib=attrib)

    def visit_moinpage_table_header(self, element):
        # TODO: Attributes conversion
        return self.new_copy(docbook.thead, element, attrib={})

    def visit_moinpage_table_footer(self, element):
        # TODO: Attributes conversion
        return self.new_copy(docbook.tfoot, element, attrib={})

    def visit_moinpage_table_row(self, element):
        # TODO: Attributes conversion
        return self.new_copy(docbook.tr, element, attrib={})

    def handle_simple_list(self, docbook_tag, element, attrib):
        list_items = []
        for child in element:
            if isinstance(child, ET.Element):
                # We do not care about <list-item>
                if child.tag.name != "list-item":
                    r = self.visit(child)
                else:
                    r = self.do_children(child)

                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                list_items.extend(r)
        return ET.Element(docbook_tag, attrib=attrib, children=list_items)

    def visit_moinpage_page(self, element):
        title = ET.Element(docbook("title"), attrib={}, children=[self.title])
        info = ET.Element(docbook.info, attrib={}, children=[title])
        for item in element:
            if item.tag.uri == moin_page and item.tag.name == "body":
                c = self.do_children(item)
                if not c:
                    self.section_children = sorted(self.section_children.items(), reverse=True)
                    section = None
                    for k, v in self.section_children:
                        if section:
                            section_tag = f"sect{k}"
                            v.append(section)
                            section = ET.Element(docbook(section_tag), attrib={}, children=v)
                        else:
                            section_tag = f"sect{k}"
                            section = ET.Element(docbook(section_tag), attrib={}, children=v)
                    return ET.Element(docbook.article, attrib={}, children=[info, section])
                else:
                    c.insert(0, info)
                    return ET.Element(docbook.article, attrib={}, children=c)

        raise RuntimeError(f"page:page need to contain exactly one page body tag, got {element[:]!r}")

    def visit_moinpage_p(self, element):
        """
        If we have a title attribute for p, we return a para,
        with a <title> child.
        Otherwise we return a <simpara>.
        """
        title_attr = element.get(html("title"))
        if title_attr:
            print(title_attr)
            children = []
            title_elem = self.new(docbook("title"), attrib={}, children=[title_attr])
            children.append(title_elem)
            children.extend(self.do_children(element))
            return self.new(docbook.para, attrib={}, children=children)
        else:
            return self.new_copy(docbook.simpara, element, attrib={})

    def visit_moinpage_span(self, element):
        """
        The span element is used in the DOM Tree to define some specific formatting.
        So each attribute will give different resulting tag.

        TODO: Add support for text-decoration attribute
        TODO: Add support for font-size attribute
        """
        # Check for the attributes of span
        for key, value in element.attrib.items():
            if key.name == "baseline-shift":
                if value == "super":
                    return self.new_copy(docbook.superscript, element, attrib={})
                if value == "sub":
                    return self.new_copy(docbook.subscript, element, attrib={})

        return self.new_copy(docbook.phrase, element, attrib={})

    def visit_moinpage_strong(self, element):
        """
        <strong> --> <emphasis role=strong>
        """
        attrib = {}
        key = docbook.role
        attrib[key] = "strong"
        return self.new_copy(docbook.emphasis, element, attrib=attrib)

    def visit_simple_tag(self, element):
        tag_to_return = self.simple_tags[element.tag.name]
        return self.new_copy(tag_to_return, element, attrib={})


default_registry.register(Converter._factory, type_moin_document, Type("application/docbook+xml"))
