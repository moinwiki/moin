# Copyright: 2010 MoinMoin:ValentinJaniaut
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - DocBook input converter
Converts a DocBook document into an internal document tree.

Currently supports DocBook v5.

Some elements of DocBook v4 specification are also supported
for backward compatibility:

- ulink
"""

import re

from emeraldtree import ElementTree as ET

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from moin.utils.iri import Iri
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page, xlink, docbook, xml, html, xinclude

from . import default_registry
from ._util import allowed_uri_scheme, decode_data, normalize_split_text

from moin import log

logging = log.getLogger(__name__)


class NameSpaceError(Exception):
    pass


def XML(text, parser=None):
    """
    Copied from EmeraldTree/tree.py to force use of local XMLParser class override.
    """
    if not parser:
        parser = XMLParser(target=ET.TreeBuilder())
    parser.feed(text)
    return parser.close()


class XMLParser(ET.XMLParser):
    """
    Override EmeraldTree/tree.py XMLParser class. Required to add auto-scroll textarea feature.

    There is no need to subclass all tree.py classes and procedures with stubs because this
    modified _start_list is only needed for the initial construction of the DOM when
    flaskg.add_lineno_attr may be True.
    """

    def _start_list(self, tag, attrib_in):
        elem = super()._start_list(tag, attrib_in)
        if flaskg and getattr(flaskg, "add_lineno_attr", False):
            elem.attrib[html.data_lineno] = self._parser.CurrentLineNumber
        return elem


class Converter:
    """
    Converter application/docbook+xml -> x.moin.document
    """

    # Namespace of our input data
    docbook_namespace = {docbook.namespace: "docbook"}

    # DocBook elements which are completely ignored by our converter
    # We even do not process children of these elements
    ignored_tags = {
        # Info elements
        "abstract",
        "artpagenums",
        "annotation",
        "artpagenums",
        "author",
        "authorgroup",
        "authorinitials",
        "bibliocoverage",
        "biblioid",
        "bibliomisc",
        "bibliomset",
        "bibliorelation",
        "biblioset",
        "bibliosource",
        "collab",
        "confdates",
        "confgroup",
        "confnum",
        "confsponsor",
        "conftitle",
        "contractnum",
        "contractsponsor",
        "copyright",
        "contrib",
        "cover",
        "edition",
        "editor",
        "extendedlink",
        "issuenum",
        "itermset",
        "keyword",
        "keywordset",
        "legalnotice",
        "org",
        "orgname",
        "orgdiv",
        "otheraddr",
        "othercredit",
        "pagenums",
        "personblurb",
        "printhistory",
        "productname",
        "productnumber",
        "pubdate",
        "publisher",
        "publishername",
        "releaseinfo",
        "revdescription",
        "revhistory",
        "revision",
        "revnumber",
        "revremark",
        "seriesvolnums",
        "subjectset",
        "volumenum",
        # Other bibliography elements
        "bibliodiv",
        "biblioentry",
        "bibliography",
        "bibliolist",
        "bibliomixed",
        "biblioref",
        "bibliorelation",
        "citation",
        "citerefentry",
        "citetitle",
        # Callout elements
        "callout",
        "calloutlist",
        "area",
        "areaset",
        "areaspec",
        "co",
        "imageobjectco",
        # Class information
        "classname",
        "classsynopsis",
        "classsynopsisinfo",
        "constructorsynopsis",
        "destructorsynopsis",
        "fieldsynopsis",
        "funcdef",
        "funcparams",
        "funcprototype",
        "funcsynopsis",
        "funcsynopsisinfo",
        "function",
        "group",
        "initializer",
        "interfacename",
        "methodname",
        "methodparam",
        "methodsynopsis",
        "ooclass",
        "ooexception",
        "oointerface",
        "varargs",
        "void",
        # GUI elements
        "guibutton",
        "guiicon",
        "guilabel",
        "guimenu",
        "guimenuitem",
        "guisubmenu",
        # EBNF Elements
        "constraint",
        "constraintdef",
        "lhs",
        "rhs",
        "nonterminal",
        # msg elements
        "msg",
        "msgaud",
        "msgentry",
        "msgexplan",
        "msginfo",
        "msglevel",
        "msgmain",
        "msgorig",
        "msgrel",
        "msgset",
        "msgsub",
        "msgtext",
        # REF entry
        "refclass",
        "refdescriptor",
        "refentry",
        "refentrytitle",
        "reference",
        "refmeta",
        "refmiscinfo",
        "refname",
        "refnamediv",
        "refpurpose",
        "refsect1",
        "refsect2",
        "refsect3",
        "refsection",
        "refsynopsisdiv",
        # TOC
        "toc",
        "tocdiv",
        "tocentry",
        # Index elements
        "index",
        "indexdiv",
        "indexentry",
        "indexterm",
        "primary",
        "primaryie",
        "secondary",
        "secondaryie",
        "see",
        "seealso",
        "tertiary",
        "tertiaryie",
        # Other elements
        "info",
        "bridgehead",
        "arc",
        "titleabbrev",
        "spanspec",
        "xref",
    }

    # DocBook inline elements which does not have equivalence in the DOM
    # tree, but we keep the information using <span element='tag.name'>
    inline_tags = {
        "abbrev",
        "address",
        "accel",
        "acronym",
        "alt",
        "affiliation",
        "city",
        "command",
        "constant",
        "country",
        "database",
        "date",
        "errorcode",
        "errorname",
        "errortext",
        "errortype",
        "exceptionname",
        "fax",
        "filename",
        "firstname",
        "firstterm",
        "foreignphrase",
        "hardware",
        "holder",
        "honorific",
        "jobtitle",
        "keycap",
        "keycode",
        "keycombo",
        "keysym",
        "lineannotation",
        "manvolnum",
        "mousebutton",
        "option",
        "optional",
        "package",
        "person",
        "personname",
        "phone",
        "pob",
        "postcode",
        "prompt",
        "remark",
        "replaceable",
        "returnvalue",
        "shortaffil",
        "shortcut",
        "state",
        "street",
        "surname",
        "symbol",
        "systemitem",
        "termdef",
        "type",
        "uri",
        "userinput",
        "wordasword",
        "varname",
        "anchor",
    }

    # DocBook block element which does not have equivalence in the DOM
    # tree, but we keep the information using <div html:class='tag.name'>
    block_tags = {
        "acknowledgements",
        "appendix",
        "article",
        "book",
        "caption",
        "chapter",
        "cmdsynopsis",
        "colophon",
        "dedication",
        "epigraph",
        "example",
        "figure",
        "equation",
        "part",
        "partintro",
        "screenshoot",
        "set",
        "setindex",
        "sidebar",
        "simplesect",
        "subtitle",
        "synopsis",
        "synopfragment",
        "task",
        "taskprerequisites",
        "taskrelated",
        "tasksummary",
        "title",
    }

    # DocBook has admonition as individual element, but the DOM Tree
    # has only one element for it, so we will convert all the DocBook
    # admonitions in this list, into the admonition element of the DOM Tree.
    admonition_tags = {"attention", "caution", "danger", "error", "hint", "important", "note", "tip", "warning"}

    # DocBook can handle three kinds of media: audio, image, video.
    # TODO: a media format attribute is optional, e.g.: <imagedata format="jpeg" fileref="jpeg.jpg"/>
    #     XXX: quality of supported formats list is suspect, see below
    media_tags = {
        # <tagname>: (<formats list>, <child tagname>, <mime type>)
        "audioobject": (
            ["x-wav", "mpeg", "ogg", "webm"],  # XXX: none of these are in http://docbook.org/tdg/en/html/audiodata.html
            "audiodata",
            "audio/",
        ),
        "imageobject": (
            ["gif", "png", "jpeg", "jpg", "svg"],  # selected from http://docbook.org/tdg/en/html/imagedata.html
            "imagedata",
            "image/",
        ),
        "videoobject": (
            ["ogg", "webm", "mp4"],  # XXX: none of these are in http://docbook.org/tdg/en/html/videodata.html
            "videodata",
            "video/",
        ),
    }

    # DocBook tags which can be convert directly to a DOM Tree element
    simple_tags = {
        "code": moin_page.code,
        "computeroutput": moin_page.code,
        "glossdef": moin_page("list-item-body"),
        "glossentry": moin_page("list-item"),
        "glosslist": moin_page("list"),
        "glossterm": moin_page("list-item-label"),
        "literal": moin_page.code,
        "markup": moin_page.code,
        "para": moin_page.p,
        "phrase": moin_page.span,
        "programlisting": moin_page.blockcode,
        "quote": moin_page.quote,
        "row": moin_page("table-row"),
        "screen": moin_page.blockcode,
        "simpara": moin_page.p,
        "term": moin_page("list-item-label"),
        "listitem": moin_page("list-item-body"),
        "thead": moin_page("table-header"),
        "tfoot": moin_page("table-footer"),
        "tbody": moin_page("table-body"),
        "tr": moin_page("table-row"),
        "variablelist": moin_page("list"),
        "varlistentry": moin_page("list-item"),
    }

    # Other block elements which can be root element.
    root_tags = {
        "blockquote",
        "formalpara",
        "informalequation",
        "informalexample",
        "informalfigure",
        "informalfigure",
        "orderedlist",
        "sect1",
        "sect2",
        "sect3",
        "sect4",
        "sect5",
        "section",
        "segmentedlist",
        "simplelist",
        "procedure",
        "qandaset",
    }

    # Regular expression to find section tag.
    sect_re = re.compile("sect[1-5]")

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, data, contenttype=None, arguments=None):
        text = decode_data(data, contenttype)
        content = normalize_split_text(text)
        docbook_str = "\n".join(content)

        # Initalize our attributes
        self.section_depth = 0
        self.heading_level = 0
        self.is_section = False

        # We store the standard attributes of an element.
        # Once we have been able to put it into an output element,
        # we clear this attribute.
        self.standard_attribute = {}

        # We will create an element tree from the DocBook content
        try:
            # XXX: The XML parser need bytestring.
            tree = XML(docbook_str.encode("utf-8"))  # using local XML override, not ET.XML
        except ET.ParseError as detail:
            return self.error(str(detail))

        try:
            if tree.tag.name in self.block_tags:
                return self.start_dom_tree(tree, 0)
            else:
                # XXX: Internationalization
                return self.error("The root element of the docbook document is not supported by the converter")
        # XXX: Error handling could probably be better.
        except NameSpaceError as detail:
            return self.error(str(detail))

    def error(self, message):
        """
        Return a DOM Tree containing an error message.
        """
        error = self.new(moin_page("error"), attrib={}, children=[message])
        part = self.new(moin_page("part"), attrib={}, children=[error])
        body = self.new(moin_page("body"), attrib={}, children=[part])
        return self.new(moin_page("page"), attrib={}, children=[body])

    def do_children(self, element, depth):
        """
        Function to process the conversion of the children of
        a given element.
        """
        new_children = []
        depth += 1
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                new_children.extend(r)
            else:
                # avoid problems in html_out by ignoring unicode '\n', '\n  ', '\n    '
                if child.strip():
                    new_children.append(child)
        return new_children

    def new(self, tag, attrib, children):
        """
        Return a new element for the DocBook Tree.
        """
        if self.standard_attribute:
            attrib.update(self.standard_attribute)
            self.standard_attribute = {}
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, depth, attrib):
        """
        Function to copy one element to the DocBook Tree.

        It first converts the children of the element,
        and then the element itself.
        """
        children = self.do_children(element, depth)
        return self.new(tag, attrib, children)

    def get_standard_attributes(self, element):
        """
        We will extract the standard attributes of the element, if any.
        We save the result in our standard attribute.
        """
        result = {}
        for key, value in element.attrib.items():
            if key.uri == xml and key.name in ["id", "base", "lang"] or key.name == "data-lineno":
                result[key] = value
        if result:
            # We clear standard_attribute, if ancestror attribute
            # was stored and has not been written in to the output,
            # anyway the new standard attributes will get higher priority
            self.standard_attribute = result

    def visit(self, element, depth):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the given namespace.
        """
        uri = element.tag.uri
        name = self.docbook_namespace.get(uri, None)
        if name is not None:
            method_name = "visit_" + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element, depth)

        # We did not recognize the namespace, we stop the conversion.
        raise NameSpaceError("Unknown namespace")

    def visit_docbook(self, element, depth):
        """
        Function called to handle the conversion of DocBook elements
        to the moin_page DOM Tree.

        We will detect the name of the tag, and pick up the correct method
        to convert it.
        """
        # Save the standard attribute of the element
        self.get_standard_attributes(element)

        # We have a section tag
        if self.sect_re.match(element.tag.name):
            result = []
            result.append(self.visit_docbook_sect(element, depth))
            result.extend(self.do_children(element, depth))
            return result

        # We have an inline element without equivalence in the DOM Tree
        if element.tag.name in self.inline_tags:
            return self.visit_docbook_inline(element, depth)

        # We have a block element without equivalence in the DOM Tree
        if element.tag.name in self.block_tags:
            return self.visit_docbook_block(element, depth)

        # We have an element easy to convert
        if element.tag.name in self.simple_tags:
            return self.visit_simple_tag(element, depth)

        # We should ignore this element
        if element.tag.name in self.ignored_tags:
            logging.warning(f"Ignored tag:{element.tag.name}")
            return

        # We have an admonition element
        if element.tag.name in self.admonition_tags:
            return self.visit_docbook_admonition(element, depth)

        # We will find the correct method to handle our tag
        method_name = "visit_docbook_" + element.tag.name
        method = getattr(self, method_name, None)
        if method:
            return method(element, depth)

        # Otherwise we process children of the unknown element
        # XXX: We should probably raise an error to have a strict converter
        return self.do_children(element, depth)

    def visit_data_object(self, element, depth):
        """
        Process a mediaobject element. Possible child tags are videoobject, audioobject, imageobject,
        caption, objectinfo, and textobject.

        <mediaobject><videoobject><videodata fileref="video.mp4"/></videoobject></mediaobject>
        """
        object_data = []
        text_object = []
        caption = []
        object_element = ""
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name in self.media_tags:  # audioobject, imageobject, videoobject
                    preferred_format, data_tag, mimetype = self.media_tags[child.tag.name]
                    object_element = child
                    for grand_child in child:
                        if isinstance(grand_child, ET.Element) and grand_child.tag.name == data_tag:
                            # capture audiodata, imagedata, or videodata tags
                            object_data.append(grand_child)
                if child.tag.name == "caption":
                    caption = self.do_children(child, depth + 1)[0]
                if child.tag.name == "textobject":
                    text_object = child
                # we ignore objectinfo tags
        return self.visit_data_element(object_element, depth, object_data, text_object, caption)

    def visit_data_element(self, element, depth, object_data, text_object, caption):
        """
        We will try to return an object element based on the
        object_data. If it is not possible, we return a paragraph
        with the content of text_object.
        """
        attrib = {}
        preferred_format, data_tag, mimetype = self.media_tags[element.tag.name]
        if not object_data:
            if not text_object:
                return
            else:
                children = self.do_children(element, depth + 1)
                return self.new(moin_page.p, attrib={}, children=children)
        # We try to determine the best object to show
        for obj in object_data:
            format = obj.get("format")  # format is optional: <imagedata format="jpeg" fileref="jpeg.jpg"/>
            if format:
                format = format.lower()
                if format in preferred_format:
                    object_to_show = obj
                    break
                else:
                    # unsupported format
                    object_to_show = None
            else:
                # XXX: Maybe we could add some verification over the extension of the file
                object_to_show = obj

        if object_to_show is None:
            # we could not find any suitable object, return the text_object replacement.
            children = self.do_children(text_object, depth + 1)
            return self.new(moin_page.p, attrib={}, children=children)

        href = object_to_show.get("fileref")
        if not href:
            # We could probably try to use entityref,
            # but at this time we won't support it.
            return
        attrib[html.alt] = href
        if "://" in href:
            attrib[xlink.href] = Iri(href)
        else:
            attrib[xinclude.href] = Iri(scheme="wiki.local", path=href)
        format = object_to_show.get("format")
        if format:
            format = format.lower()
            attrib[moin_page("type")] = "".join([mimetype, format])
        else:
            attrib[moin_page("type")] = mimetype
        align = object_to_show.get("align")
        if align and align in {"left", "center", "right", "top", "middle", "bottom"}:
            attrib[html.class_] = align

        # return object tag, html_out.py will convert to img, audio, or video based on type attr
        ret = ET.Element(xinclude.include, attrib=attrib)
        if caption:
            caption = self.new(moin_page.span, attrib={moin_page.class_: "db-caption"}, children=[caption])
            return self.new(moin_page.span, attrib={}, children=[ret, caption])
        else:
            return ret

    def visit_docbook_admonition(self, element, depth):
        """
        <tag.name> --> <admonition type='tag.name'>
        """
        attrib = {}
        key = moin_page("type")
        attrib[key] = element.tag.name
        return self.new_copy(moin_page.admonition, element, depth, attrib=attrib)

    def visit_docbook_block(self, element, depth):
        """
        Convert a block element which does not have equivalence
        in the DOM Tree.

        <tag.name> --> <div html:class="db-tag.name">
        """
        attrib = {}
        key = html.class_
        attrib[key] = "".join(["db-", element.tag.name])
        return self.new_copy(moin_page.div, element, depth, attrib=attrib)

    def visit_docbook_blockquote(self, element, depth):
        """
        <blockquote>
          <attribution>Author</attribution>
          Text
        </blockquote>
          --> <blockquote source="Author">Text</blockquote>

        <blockquote>Text</blockquote>
          --> <blockquote source="Unknow">Text</blockquote>
        """
        # TODO: Translate
        source = "Unknow"
        children = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == "attribution":
                    source = self.do_children(child, depth + 1)
                else:
                    children.extend(self.do_children(child, depth + 1))
            else:
                children.append(child)
        attrib = {}
        attrib[moin_page("source")] = source[0]
        return self.new(moin_page.blockquote, attrib=attrib, children=children)

    def visit_docbook_emphasis(self, element, depth):
        """
        emphasis element, is the only way to apply some style
        on a DocBook element directly from the DocBook tree.

        Basically, you can use it for "italic" and "bold" style.

        However, it is still semantic, so we call it emphasis and strong.
        """
        for key, value in element.attrib.items():
            if key.name == "role" and value == "bold":
                return self.new_copy(moin_page.strong, element, depth, attrib={})
        return self.new_copy(moin_page.emphasis, element, depth, attrib={})

    def visit_docbook_entrytbl(self, element, depth):
        """
        Return a table within a table-cell.
        """
        table_element = self.new_copy(moin_page.table, element, depth, attrib={})
        return self.new(moin_page("table-cell"), attrib={}, children=[table_element])

    def visit_docbook_footnote(self, element, depth):
        """
        <footnote> --> <note note-class="footnote"><note-body>
        """
        attrib = {}
        key = moin_page("note-class")
        attrib[key] = "footnote"
        children = self.new(moin_page("note-body"), attrib={}, children=self.do_children(element, depth))
        if len(children) > 1:
            # must delete lineno because footnote will be placed near end of page and out of sequence
            del children._children[1].attrib[html.data_lineno]
        return self.new(moin_page.note, attrib=attrib, children=[children])

    def visit_docbook_formalpara(self, element, depth):
        """
        <formalpara>
          <title>Heading</title>
          <para>Text</para>
        </formalpara>
          --> <p html:title="Heading">Text</p>
        """
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == "title":
                    title_element = child
                if child.tag.name == "para":
                    para_element = child

        if not title_element:
            # XXX: Improve error
            raise SyntaxError("title child missing for formalpara element")
        if not para_element:
            # XXX: Improve error
            raise SyntaxError("para child missing for formalpara element")

        children = self.do_children(para_element, depth + 1)[0]
        attrib = {}
        attrib[html("title")] = title_element[0]
        return self.new(moin_page.p, attrib=attrib, children=children)

    def visit_docbook_informalequation(self, element, depth):
        """
        <informalequation> --> <div html:class="equation">
        """
        attrib = {}
        attrib[html.class_] = "db-equation"
        return self.new_copy(moin_page("div"), element, depth, attrib=attrib)

    def visit_docbook_informalexample(self, element, depth):
        """
        <informalexample> --> <div html:class="example">
        """
        attrib = {}
        attrib[html.class_] = "db-example"
        return self.new_copy(moin_page("div"), element, depth, attrib=attrib)

    def visit_docbook_informalfigure(self, element, depth):
        """
        <informalfigure> --> <div html:class="figure">
        """
        attrib = {}
        attrib[html.class_] = "db-figure"
        return self.new_copy(moin_page("div"), element, depth, attrib=attrib)

    def visit_docbook_inline(self, element, depth):
        """
        For some specific tags (defined in inline_tags)
        We just return <span element="tag.name">
        """
        key = html.class_
        attrib = {}
        attrib[key] = "".join(["db-", element.tag.name])
        return self.new_copy(moin_page.span, element, depth, attrib=attrib)

    def visit_docbook_inlinequation(self, element, depth):
        """
        <inlinequation> --> <span element="equation">
        """
        attrib = {}
        attrib[moin_page("element")] = "equation"
        return self.new_copy(moin_page.span, element, depth, attrib=attrib)

    def visit_docbook_inlinemediaobject(self, element, depth):
        data_element = self.visit_data_object(element, depth)
        attrib = {html.class_: "db-inlinemediaobject"}
        return self.new(moin_page.span, attrib=attrib, children=[data_element])

    def visit_docbook_itemizedlist(self, element, depth):
        """
        <itemizedlist> --> <list item-label-generate="unordered">
        """
        attrib = {}
        key = moin_page("item-label-generate")
        attrib[key] = "unordered"
        return self.visit_simple_list(moin_page.list, attrib, element, depth)

    def visit_docbook_link(self, element, depth):
        """
        LINK Conversion.

        There is two kind of links in DocBook :
        One using the xlink namespace.
        The other one using linkend attribute.

        The xlink attributes can directly be used in the <a> tag of the
        DOM Tree since we support xlink.

        For the linkend attribute, we need to have a system supporting
        the anchors.
        """
        attrib = {}
        if element.attrib.get(xlink.title_):
            attrib[html.title_] = element.attrib.get(xlink.title_)
        href = element.attrib.get(xlink.href)
        linkend = element.get("linkend")
        if linkend:
            href = "".join(["#", linkend])
        iri = Iri(href)
        if iri.scheme is None:
            iri.scheme = "wiki.local"
        attrib[xlink.href] = iri
        return self.new_copy(moin_page.a, element, depth, attrib)

    def visit_docbook_literallayout(self, element, depth):
        """
        <literallayout> --> <blockcode html:class="db-literallayout">
        """
        attrib = {html.class_: "db-literallayout"}
        return self.new_copy(moin_page.blockcode, element, depth, attrib=attrib)

    def visit_docbook_mediaobject(self, element, depth):
        data_element = self.visit_data_object(element, depth)
        attrib = {html.class_: "db-mediaobject"}
        return self.new(moin_page.div, attrib=attrib, children=[data_element])

    def visit_docbook_olink(self, element, depth):
        """
        <olink targetdoc='URI' targetptr='ptr'>
          --> <a xlink:href='URI#ptr'>
        """
        targetdoc = element.get("targetdoc")
        targetptr = element.get("targetptr")
        if targetdoc and targetptr and allowed_uri_scheme(targetdoc):
            attrib = {}
            attrib[xlink.href] = "".join([targetdoc, "#", targetptr])
            return self.new_copy(moin_page.a, element, depth, attrib=attrib)

    def visit_docbook_orderedlist(self, element, depth):
        """
        <orderedlist> --> <list item-label-generate="ordered">
        See attribute_conversion for more details about the attributes.
        """
        attrib = {}
        key = moin_page("item-label-generate")
        attrib[key] = "ordered"
        attribute_conversion = {
            "upperalpha": "upper-alpha",
            "loweralpha": "lower-alpha",
            "upperroman": "upper-roman",
            "lowerroman": "lower-roman",
        }
        numeration = element.get("numeration")
        if numeration in attribute_conversion:
            key = moin_page("list-style-type")
            attrib[key] = attribute_conversion[numeration]
        return self.visit_simple_list(moin_page.list, attrib, element, depth)

    def visit_docbook_sbr(self, element, depth):
        """
        <sbr /> --> <line-break />
        """
        return self.new(moin_page("line-break"), attrib={}, children={})

    def visit_docbook_sect(self, element, depth):
        """
        This is the function to convert a numbered section.

        Numbered section uses tag like <sectN> where N is the number
        of the section between 1 and 5.

        The sections are supposed to be correctly nested.

        We only convert a section to an heading if one of the children
        is a title element.

        TODO: See if we can unify with recursive section below.
        TODO: Add div element, with specific id
        """
        self.is_section = True
        title = ""
        for child in element:
            if isinstance(child, ET.Element):
                uri = child.tag.uri
                name = self.docbook_namespace.get(uri, None)
                if name == "docbook" and child.tag.name == "title":
                    title = child
                    # Remove the title element to avoid double conversion
                    element.remove(child)
        heading_level = element.tag.name[4]
        key = moin_page("outline-level")
        attrib = {}
        attrib[key] = heading_level
        return self.new(moin_page.h, attrib=attrib, children=title)

    def visit_docbook_section(self, element, depth):
        """
        This is the function to convert recursive section.

        Recursive section use tag like <section> only.

        Each section, inside another section is a subsection.

        To convert it, we will use the depth of the element, and
        two attributes of the converter which indicate the
        current depth of the section and the current level heading.
        """
        self.is_section = True
        if depth > self.section_depth:
            self.section_depth += 1
            self.heading_level += 1
        elif depth < self.section_depth:
            self.heading_level = self.heading_level - (self.section_depth - depth)
            self.section_depth = depth

        title = ""
        result = []
        for child in element:
            if isinstance(child, ET.Element):
                uri = child.tag.uri
                name = self.docbook_namespace.get(uri, None)
                if name == "docbook" and child.tag.name == "title":
                    title = child
                    # Remove the title element to avoid double conversion
                    element.remove(child)
        key = moin_page("outline-level")
        attrib = {}
        attrib[key] = self.heading_level
        result.append(self.new(moin_page.h, attrib=attrib, children=title))
        result.extend(self.do_children(element, depth))
        return result

    def visit_docbook_seglistitem(self, element, labels, depth):
        """
        A seglistitem is a list-item for a segmented list. It is quite
        special because it act list definition with label, but the labels
        are predetermined in the labels list.

        So we generate label/body couple according to the content in
        labels
        """
        new = []
        counter = 0
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == "seg":
                    label_tag = ET.Element(
                        moin_page("list-item-label"), attrib={}, children=labels[counter % len(labels)]
                    )
                    body_tag = ET.Element(moin_page("list-item-body"), attrib={}, children=self.visit(child, depth))
                    item_tag = ET.Element(moin_page("list-item"), attrib={}, children=[label_tag, body_tag])
                    item_tag = (item_tag,)
                    new.extend(item_tag)
                    counter += 1
                else:
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    new.extend(r)
            else:
                new.append(child)
        return new

    def visit_docbook_segmentedlist(self, element, depth):
        """
        A segmented list is a like a list of definition, but the label
        are defined at the start with <segtitle> tag and then for each
        definition, we repeat the label.

        So to convert such list, we will first determine and save the
        labels. Then we will iterate over the object to get the
        definition.
        """
        labels = []
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = None
                if child.tag.name == "segtitle":
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    labels.extend(r)
                else:
                    if child.tag.name == "seglistitem":
                        r = self.visit_docbook_seglistitem(child, labels, depth)
                    else:
                        r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    new.extend(r)
            else:
                new.append(child)
        return ET.Element(moin_page.list, attrib={}, children=new)

    def visit_docbook_simplelist(self, element, depth):
        """
        <simplelist> --> <list item-label-generate="unordered">
        """
        # TODO: Add support of the type attribute
        attrib = {}
        key = moin_page("item-label-generate")
        attrib[key] = "unordered"
        return self.visit_simple_list(moin_page.list, attrib, element, depth)

    def visit_docbook_subscript(self, element, depth):
        """
        <subscript> --> <span baseline-shift="sub">
        """
        attrib = {}
        key = moin_page("baseline-shift")
        attrib[key] = "sub"
        return self.new_copy(moin_page.span, element, depth, attrib=attrib)

    def visit_docbook_substeps(self, element, depth):
        """
        Return the same elements than a procedure
        """
        return self.visit_docbook_procedure(element, depth)

    def visit_docbook_superscript(self, element, depth):
        """
        <superscript> --> <span baseline-shift="super">
        """
        attrib = {}
        key = moin_page("baseline-shift")
        attrib[key] = "super"
        return self.new_copy(moin_page.span, element, depth, attrib=attrib)

    def visit_docbook_procedure(self, element, depth):
        """
        <procedure> --> <list item-label-generate="ordered">
        """
        # TODO: See to add Procedure text (if needed)
        attrib = {}
        key = moin_page("item-label-generate")
        attrib[key] = "ordered"
        return self.visit_simple_list(moin_page.list, attrib, element, depth)

    def visit_docbook_qandaset(self, element, depth):
        """
        See visit_qandaset_* method.
        """
        default_label = element.get("defaultlabel")
        if default_label == "number":
            return self.visit_qandaset_number(element, depth)
        elif default_label == "qanda":
            return self.visit_qandaset_qanda(element, depth)
        else:
            return self.do_children(element, depth)

    def visit_docbook_table(self, element, depth):
        """
        <table> --> <table>
        """
        # we should not have any strings in the child
        list_table_elements = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                list_table_elements.extend(r)
        return ET.Element(moin_page.table, attrib={}, children=list_table_elements)

    def visit_docbook_tag(self, element, depth):
        """
        <tag class="class.name" namespace="ns.address">TAG</tag>
          --> <span class="db-tag-class.name">{ns.address}TAG</tag>
        """
        # We get the attributes
        class_attribute = element.get("class")
        namespace_attribute = element.get("namespace")
        # We create the attribute for our final element
        attrib = {}
        children = []
        if class_attribute:
            attrib[html.class_] = "".join(["db-tag-", class_attribute])
        else:
            attrib[html.class_] = "db-tag"
        if namespace_attribute:
            namespace_str = "".join(["{", namespace_attribute, "}"])
            children.append(namespace_str)
        children.extend(self.do_children(element, depth))
        return self.new(moin_page.span, attrib=attrib, children=children)

    def visit_docbook_trademark(self, element, depth):
        """
        Depending of the trademark class, a specific entities is added to the string.

        Docbook supports 4 types of trademark: copyright, registered, trade (mark), and service (mark).
        <trademark> --> <span class="db-trademark">
        """
        trademark_entities = {
            "copyright": "\xa9 ",  # '&copy; ',
            "registered": "\xae",  # '&reg;',
            "trade": "\u2122",  # no entity name defined for superscript TM
        }
        trademark_class = element.get("class")
        children = self.do_children(element, depth)
        if trademark_class in trademark_entities:
            if trademark_class == "copyright":
                children.insert(0, trademark_entities[trademark_class])
            else:
                children.append(trademark_entities[trademark_class])
        elif trademark_class == "service":
            # no entity name nor entity number defined for superscript SM
            sup_attrib = {moin_page("baseline-shift"): "super"}
            service_mark = self.new(moin_page.span, attrib=sup_attrib, children=["SM"])
            children.append(service_mark)
        attrib = {html.class_: "db-trademark"}
        return self.new(moin_page.span, attrib=attrib, children=children)

    def visit_docbook_entry(self, element, depth):
        """
        <entry> --> <table-cell>
        """
        attrib = {}
        rowspan = element.get("morerows")
        colspan = element.get("morecols")
        try:
            if rowspan:
                attrib[moin_page.number_rows_spanned] = str(1 + int(rowspan))
            if colspan:
                attrib[moin_page.number_columns_spanned] = str(1 + int(colspan))
        except ValueError:
            pass
        return self.new_copy(moin_page.table_cell, element, depth, attrib=attrib)

    def visit_docbook_td(self, element, depth):
        """
        <td> --> <table-cell>
        """
        attrib = {}
        rowspan = element.get("rowspan")
        colspan = element.get("colspan")
        if rowspan:
            attrib[moin_page.number_rows_spanned] = rowspan
        if colspan:
            attrib[moin_page.number_columns_spanned] = colspan
        return self.new_copy(moin_page.table_cell, element, depth, attrib=attrib)

    def visit_docbook_ulink(self, element, depth):
        """
        NB : <ulink> is not a part of DocBook v.5 however we
        support it in our converter since it is still widely used
        and it helps to keep a compatibility with DocBook v.4
        """
        attrib = {}
        href = element.get(docbook.url)
        # Since it is an element of DocBook v.4,
        # The namespace does not always work, so we will try to retrive the attribute whatever
        if not href:
            for key, value in element.attrib.items():
                if key.name == "url" and allowed_uri_scheme(value):
                    href = value
        key = xlink.href
        attrib[key] = href
        return self.new_copy(moin_page.a, element, depth, attrib=attrib)

    def visit_qandaentry_number(self, element, depth):
        """
        Convert::

            <question>Q</question><answer>A</answer>

        to::

            <list-item>
                <list-item-body><p>Q</p><p>A</p></list-item-body>
            </list-item>
        """
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == "question" or child.tag.name == "answer":
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    items.extend(r)
            else:
                items.append(child)

        item_body = ET.Element(moin_page("list-item-body"), attrib={}, children=items)
        return ET.Element(moin_page("list-item"), attrib={}, children=[item_body])

    def visit_qandaset_number(self, element, depth):
        """
        <qandaset defaultlabel="number">
          --> <list item-label-generate='ordered'>
        """
        attrib = {}
        key = moin_page("item-label-generate")
        attrib[key] = "ordered"
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == "qandaentry":
                    r = self.visit_qandaentry_number(child, depth)
                else:
                    r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page("list"), attrib=attrib, children=items)

    def visit_qandaentry_qanda(self, element, depth):
        """
        Convert::

            <question>Q body</question><answer>A Body</answer>

        to::

            <list-item>
                <list-item-label>Q:</list-item-label>
                <list-item-body>Q Body</list-item-body>
            </list-item>
            <list-item>
                <list-item-label>A:</list-item-label>
                <list-item-body>A Body</list-item-body>
            </list-item>
        """
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = ()
                item_label = None
                if child.tag.name == "question":
                    item_label = ET.Element(moin_page("list-item-label"), attrib={}, children="Q:")
                elif child.tag.name == "answer":
                    item_label = ET.Element(moin_page("list-item-label"), attrib={}, children="A:")
                else:
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    items.extend(r)
                if item_label is not None:
                    item_body = ET.Element(moin_page("list-item-body"), attrib={}, children=self.visit(child, depth))
                    r = (item_label, item_body)
                    list_item = ET.Element(moin_page("list-item"), attrib={}, children=r)
                    items.append(list_item)
            else:
                items.append(child)
        return items

    def visit_qandaset_qanda(self, element, depth):
        """
        <qandaset defaultlabel="qanda"> --> <list>
        """
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = ()
                if child.tag.name == "qandaentry":
                    r = self.visit_qandaentry_qanda(child, depth)
                else:
                    r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page("list"), attrib={}, children=items)

    def visit_simple_list(self, moin_page_tag, attrib, element, depth):
        """
        There is different list element in DocBook with different
        semantic meaning, but with an unique result in the DOM Tree.

        Here we handle the conversion of such of list.
        """
        list_item_tags = {"listitem", "step", "stepalternatives", "member"}
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name in list_item_tags:
                    children = self.visit(child, depth)
                    list_item_body = ET.Element(moin_page("list-item-body"), attrib={}, children=children)
                    tag = ET.Element(moin_page("list-item"), attrib={}, children=[list_item_body])
                    tag = (tag,)
                    items.extend(tag)
                else:
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r,)
                    items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page.list, attrib=attrib, children=items)

    def visit_simple_tag(self, element, depth):
        """
        Some docbook tags can be converted directly to an equivalent
        DOM Tree element. We retrieve the equivalent tag from the
        simple_tags dictionnary defined at the begining of this file.
        """
        tag_to_return = self.simple_tags[element.tag.name]
        return self.new_copy(tag_to_return, element, depth, attrib={})

    def start_dom_tree(self, element, depth):
        """
        Return the root element of the DOM tree, with all the children.

        We also add a <table-of-content> element if needed.
        """
        attrib = {}
        if self.standard_attribute:
            attrib.update(self.standard_attribute)
            self.standard_attribute = {}
        children = []
        children.append(self.visit(element, depth))
        # We show the table of content only if it is not empty
        if self.is_section:
            children.insert(0, self.new(moin_page("table-of-content"), attrib={}, children={}))
        body = self.new(moin_page.body, attrib={}, children=children)
        return self.new(moin_page.page, attrib=attrib, children=[body])


default_registry.register(Converter._factory, Type("application/docbook+xml"), type_moin_document)
