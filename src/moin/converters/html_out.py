# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - HTML output converter

Converts an internal document tree into a HTML tree.
"""

import re

from flask import current_app as app
from flask import g as flaskg
from emeraldtree import ElementTree as ET
from urllib.parse import urlencode
from babel import Locale

from moin import wikiutil
from moin.i18n import _
from moin.items import Item
from moin.utils.iri import Iri
from moin.utils.tree import html, moin_page, xlink, xml
from moin.constants.contenttypes import CONTENTTYPE_NONEXISTENT, CHARSET
from moin.utils.mime import Type, type_moin_document
from moin.constants.keys import LANGUAGE

from . import default_registry, ElementException

from moin import log

logging = log.getLogger(__name__)


# strings not allowed in style attributes
SUSPECT = {"/*", "/>", "\\", "`", "script", "&#", "http", "expression", "behavior"}


def style_attr_filter(style):
    """
    If allow_style_attributes option is True check style attribute for suspect strings, else return ''.
    """
    if app.cfg.allow_style_attributes:
        s = "".join(style.strip().lower().split())
        if any(x in s for x in SUSPECT):
            return " /*style suppressed, failed test for suspect strings*/ "
        return style
    return ""


def convert_getlink_to_showlink(href):
    """
    If the incoming transclusion reference is within this domain, then remove "+get/<revision number>/".
    """
    if href.startswith("/"):
        return re.sub(r"\+get/\+[0-9a-fA-F]+/", "", href)
    return href


def mark_item_as_transclusion(elem, href_or_item):
    """
    Return elem after adding a "moin-transclusion" class and a "data-href" attribute with
    a link to the transcluded item.

    On the client side, a Javascript function will wrap the element (or a parent element)
    in a span or div and 2 overlay siblings will be created.
    """
    if isinstance(href_or_item, Item):
        query = urlencode({"do": "show"}, encoding=CHARSET)
        href = Iri(scheme="wiki", authority="", path="/" + href_or_item.fqname.fullname, query=query)
        if hasattr(href_or_item, "meta") and LANGUAGE in href_or_item.meta:
            elem.attrib[html.lang] = href_or_item.meta[LANGUAGE]
        elif hasattr(flaskg.user, LANGUAGE):
            elem.attrib[html.lang] = flaskg.user.language
        else:
            elem.attrib[html.lang] = app.cfg.language_default
        elem.attrib[html.dir] = Locale(elem.attrib[html.lang]).text_direction
    else:  # isinstance(href_or_item, Iri)
        href = href_or_item
    elem.attrib[html.data_href] = href
    classes = elem.attrib.get(html.class_, "").split()
    classes.append("moin-transclusion")
    elem.attrib[html.class_] = " ".join(classes)
    return elem


class Attribute:
    """Adds the attribute with the HTML namespace to the output."""

    __slots__ = "key"

    def __init__(self, key):
        self.key = html(key)

    def __call__(self, value, out):
        out[self.key] = value


class Attributes:
    namespaces_valid_output = frozenset([html])

    visit_class = Attribute("class")
    visit_number_columns_spanned = Attribute("colspan")
    visit_number_rows_spanned = Attribute("rowspan")
    visit_style = Attribute("style")
    visit_title = Attribute("title")
    visit_id = Attribute("id")
    visit_type = Attribute("type")  # IE8 needs <object... type="image/svg+xml" ...> to display svg images

    def __init__(self, element):
        self.element = element

        # Detect if we either namespace of the element matches the input or the
        # output.
        self.default_uri_input = self.default_uri_output = None
        if element.tag.uri == moin_page:
            self.default_uri_input = element.tag.uri
        if element.tag.uri in self.namespaces_valid_output:
            self.default_uri_output = element.tag.uri

    def get(self, name):
        ret = self.element.get(moin_page(name))
        if ret:
            return ret
        if self.default_uri_input:
            return self.element.get(name)

    def convert(self):
        new = {}
        new_default = {}

        for key, value in self.element.attrib.items():
            if key == html.style:
                value = style_attr_filter(value)
            if key.uri == moin_page:
                # We never have _ in attribute names, so ignore them instead of
                # create ambigues matches.
                if "_" not in key.name:
                    n = "visit_" + key.name.replace("-", "_")
                    f = getattr(self, n, None)
                    if f is not None:
                        f(value, new)
            elif key.uri in self.namespaces_valid_output:
                new[key] = value
            # We convert xml:id
            elif key.uri == xml.namespace:
                if key.name == "id" or key.name == "lang":
                    new[ET.QName(key.name, html.namespace)] = value
            elif key.uri is None:
                if self.default_uri_input and "_" not in key.name:
                    n = "visit_" + key.name.replace("-", "_")
                    f = getattr(self, n, None)
                    if f is not None:
                        f(value, new_default)
                elif self.default_uri_output:
                    new_default[ET.QName(key.name, self.default_uri_output)] = value

        # Attributes with namespace overrides attributes with empty namespace.
        new_default.update(new)

        return new_default


class Converter:
    """
    Converter application/x.moin.document -> application/x.moin.document
    """

    namespaces_visit = {moin_page: "moinpage"}

    # Inline tags which can be directly converted into an HTML element
    direct_inline_tags = {"abbr", "address", "dfn", "kbd"}

    def __call__(self, element):
        return self.visit(element)

    def do_children(self, element):
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

    def new_copy(self, tag, element, attrib={}):
        attrib_new = Attributes(element).convert()
        attrib_new.update(attrib)
        children = self.do_children(element)
        return tag(attrib_new, children)

    def visit(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            n = "visit_" + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)

        # Element with unknown namespaces are just copied
        return self.new_copy(elem.tag, elem)

    def visit_moinpage(self, elem):
        n = "visit_moinpage_" + elem.tag.name.replace("-", "_")
        f = getattr(self, n, None)
        if f:
            return f(elem)

        # Unknown element are just copied
        return self.new_copy(elem.tag, elem)

    def visit_moinpage_a(self, elem):
        attrib = {}
        href = elem.get(xlink.href)
        if href:
            attrib[html.href] = href
        if len(elem) == 1 and isinstance(elem[0], str) and elem[0] == "":
            # input similar to [[#Heading]] will create an invisible link like <a href="#Heading></a> unless we fix it
            elem[0] = href.path[1:] if href.path else href.fragment
        # html attributes are copied by default (html.target, html.class, html.download...
        return self.new_copy(html.a, elem, attrib)

    def visit_moinpage_admonition(self, elem):
        """Used by reST and docbook."""
        attrib = {}
        valid_classes = {"attention", "caution", "danger", "error", "hint", "important", "note", "tip", "warning"}
        cls = elem.get(moin_page.type)
        if cls in valid_classes:
            attrib[html.class_] = cls
        elem.attrib = {}
        return self.new_copy(html.div, elem, attrib)

    def visit_moinpage_audio(self, elem):
        href = elem.get(xlink.href, None)
        attrib = {html.src: href} if href else {}
        return self.new_copy(html.audio, elem, attrib)

    def visit_moinpage_video(self, elem):
        href = elem.get(xlink.href, None)
        attrib = {html.src: href} if href else {}
        return self.new_copy(html.video, elem, attrib)

    def visit_moinpage_nowiki(self, elem):
        """
        Avoid creation of a div used only for its data-lineno attrib.
        """
        if elem.attrib.get(html.data_lineno, None) and isinstance(elem[0][0], ET.Element):
            # {{{#!wiki\ntext\n}}}
            elem[0][0].attrib[html.data_lineno] = elem.attrib[html.data_lineno]
            elem[0][0].attrib[moin_page.class_] = elem[0][0].attrib.get(moin_page.class_, "") + " moin-nowiki"
            return self.do_children(elem)
        if elem.attrib.get(html.data_lineno, None) and isinstance(elem[0][0], str) and isinstance(elem[0], ET.Element):
            # {{{\ntext\n}}} OR {{{#!highlight python\ndef xx:\n}}}
            elem[0].attrib[html.data_lineno] = elem.attrib[html.data_lineno]
            elem[0].attrib[moin_page.class_] = elem[0].attrib.get(moin_page.class_, "") + " moin-nowiki"
            return self.do_children(elem)
        # {{{\n{{{{{\ntext\n}}}}}\n}}}  # data_lineno not available, parent will have class=moin-nowiki
        return self.new_copy(html.div, elem)

    def visit_moinpage_blockcode(self, elem):
        return self.new_copy(html.pre, elem)

    def visit_moinpage_blockquote(self, elem):
        return self.new_copy(html.blockquote, elem)

    def visit_moinpage_block_comment(self, elem):
        # ## a block comment in wiki page source is suppressed here
        return

    def visit_moinpage_code(self, elem):
        return self.new_copy(html.code, elem)

    def visit_moinpage_del(self, elem):
        return self.new_copy(html.del_, elem)

    def visit_moinpage_div(self, elem):
        return self.new_copy(html.div, elem)

    def visit_moinpage_emphasis(self, elem):
        return self.new_copy(html.em, elem)

    def visit_moinpage_figure(self, elem):
        return self.new_copy(html.figure, elem)

    def visit_moinpage_figcaption(self, elem):
        return self.new_copy(html.figcaption, elem)

    def visit_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException("page:outline-level needs to be an integer")
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = self.new_copy(html(f"h{level}"), elem)
        ret.level = level
        return ret

    def visit_moinpage_inline_part(self, elem):
        body = error = None

        for item in elem:
            if item.tag.uri == moin_page:
                if item.tag.name == "inline-body":
                    body = item
                elif item.tag.name == "error":
                    error = item

        if body:
            return self.new_copy(html.span, item)

        if error:
            if len(error):
                ret = html.span(children=error)
            else:
                ret = html.span(children=("Error",))
            ret.set(html.class_, "moin-error")
            return ret

        # XXX: Move handling of namespace-less attributes into emeraldtree
        alt = elem.get(moin_page.alt, elem.get("alt"))
        if alt:
            return html.span(children=(alt,))

        return html.span()

    def visit_moinpage_ins(self, elem):
        return self.new_copy(html.ins, elem)

    def visit_moinpage_line_break(self, elem):
        # TODO: attributes?
        return html.br()

    def visit_moinpage_line_blk(self, elem):
        return self.new_copy(html.div, elem, attrib={html.class_: "moin-line-blk"})

    def visit_moinpage_line_block(self, elem):
        """
        Used for reST similar to:

        | roses are red,
        | violets are blue,
        """
        return self.new_copy(html.div, elem, attrib={html.class_: "moin-line-block"})

    def visit_moinpage_list(self, elem):
        attrib = Attributes(elem)
        attrib_new = attrib.convert()
        generate = attrib.get("item-label-generate")

        if generate:
            if generate == "ordered":
                style = attrib.get("list-style-type")
                if style:
                    if style == "upper-alpha":
                        attrib_new[html("class")] = "moin-upperalpha-list"
                    elif style == "upper-roman":
                        attrib_new[html("class")] = "moin-upperroman-list"
                    elif style == "lower-roman":
                        attrib_new[html("class")] = "moin-lowerroman-list"
                    elif style == "lower-alpha":
                        attrib_new[html("class")] = "moin-loweralpha-list"
                start_number = attrib.get("list-start")
                if start_number:
                    attrib_new[html("start")] = start_number
                ret = html.ol(attrib_new)
            elif generate == "unordered":
                style = attrib.get("list-style-type")
                if style and style == "no-bullet":
                    attrib_new[html("class")] = "moin-nobullet-list"
                ret = html.ul(attrib=attrib_new)
            else:
                raise ElementException(f'page:item-label-generate does not support "{generate}"')
        else:
            ret = html.dl(attrib=attrib_new)

        for item in elem:
            if isinstance(item, ET.Element):
                if item.tag.uri == moin_page and item.tag.name == "list-item":
                    if not generate:
                        for label in item:
                            if isinstance(label, ET.Element):
                                if label.tag.uri == moin_page and label.tag.name == "list-item-label":
                                    ret_label = self.new_copy(html.dt, label)
                                    ret.append(ret_label)
                    for body in item:
                        if isinstance(body, ET.Element):
                            if body.tag.uri == moin_page and body.tag.name == "list-item-body":
                                if generate:
                                    ret_body = self.new_copy(html.li, body)
                                else:
                                    ret_body = self.new_copy(html.dd, body)
                                ret.append(ret_body)
                                break
        return ret

    def visit_moinpage_list_item(self, elem):
        """
        Used for markdown definition lists.

        Compared to moinwiki and reST parsers, the markdown parser creates definition lists using only one
        list-item tag.name for entire list where moinwiki and reST have one list-item tag.name for
        each entry in list.
        """
        attrib = Attributes(elem)
        attrib_new = attrib.convert()
        ret = html.dl(attrib=attrib_new)
        for item in elem:
            if isinstance(item, ET.Element) and item.tag.uri == moin_page:
                if item.tag.name == "list-item-label":
                    ret.append(self.new_copy(html.dt, item))
                elif item.tag.name == "list-item-body":
                    ret.append(self.new_copy(html.dd, item))
        return ret

    def eval_object_type(self, mimetype, href):
        """
        Returns the type of an object as a str, one of the following: img, video, audio, object
        """
        if Type("image/").issupertype(mimetype):
            return "img"
        elif Type("video/").issupertype(mimetype):
            return "video"
        elif Type("audio/").issupertype(mimetype):
            return "audio"
        else:
            # Nothing else worked...try using <object>
            return "object"

    def visit_moinpage_object(self, elem):
        """
        elem of type img are converted to img tags here, others are left as object tags.

        We do not use Attributes.convert to convert all attributes, but copy selected attributes
        and follow html5 rules to place right attributes within img and object tags.
        """
        href = elem.get(xlink.href, None)
        attrib = {}

        whitelist = ["width", "height", "alt", "class", "data-href", "style", "title"]
        for key in elem.attrib:
            if key.name in whitelist:
                if key.name == "style":
                    attrib[key] = style_attr_filter(elem.attrib[key])
                else:
                    attrib[key] = elem.attrib[key]
        mimetype = Type(_type=elem.get(moin_page.type_, CONTENTTYPE_NONEXISTENT))
        if elem.get(moin_page.type_):
            del elem.attrib[moin_page.type_]
        # Get the object type
        obj_type = self.eval_object_type(mimetype, href)

        # The attribute source attribute for img,video, and audio is the same (src)
        # <object>'s attribute is 'data'
        attr = html.src if obj_type != "object" else html.data

        # The return element
        new_elem = None

        if href is not None:
            # Set the attribute of the returned element appropriately
            attrib[attr] = href
        alt = convert_getlink_to_showlink(str(href))
        alt = re.sub(r"^/", "", alt)

        if obj_type == "img":
            # Images must have alt attribute in html5, but if user did not specify then default to url
            if not attrib.get(html.alt):
                attrib[html.alt] = alt
            new_elem = html.img(attrib=attrib)

        else:
            if obj_type != "object":
                # Non-objects like video and audio have the "controls" attribute
                attrib[html.controls] = "controls"
                new_elem = self.new_copy(getattr(html, obj_type), elem, attrib)
            else:
                # is an object
                new_elem = html.object(attrib=attrib)
            # alt attr is invalid within object, audio, and video tags , append alt text to existing child
            # alt text will be transclusion alt field, item meta summary, or item name
            if new_elem.attrib.get(html.alt):
                if new_elem.text:
                    new_elem.append(" - ")
                new_elem.append(new_elem.attrib.get(html.alt))
                del new_elem.attrib[html.alt]
            else:
                if new_elem.text:
                    new_elem.append(" - ")
                new_elem.append(alt)

        if obj_type == "object" and getattr(href, "scheme", None):
            # items similar to {{http://moinmo.in}} are marked here, other objects are marked in include.py
            return mark_item_as_transclusion(new_elem, href)
        return new_elem

    def visit_moinpage_p(self, elem):
        return self.new_copy(html.p, elem)

    def visit_moinpage_page(self, elem):
        for item in elem:
            if item.tag.uri == moin_page and item.tag.name == "body":
                # if this is a transcluded page, we must pass the class and data-href attribs
                attribs = elem.attrib.copy()
                if moin_page.page_href in attribs:
                    del attribs[moin_page.page_href]
                if attribs and len(item) == 1:

                    if item[0].tag.name in ("object", "a"):
                        # png, jpg, gif are objects here, will be changed to img when they are processed
                        # transclusion is a single inline element "My pet {{bird.jpg}} flys." or
                        # "[[SomePage|{{Logo.png}}]]"
                        return self.new_copy(html.span, item, attribs)

                    elif item[0].tag.name == "p":
                        # transclusion is a single p-tag that can be coerced to inline  "Yes, we have {{no}} bananas."
                        new_span = html.span(children=item[0][:])
                        return self.new_copy(html.span, new_span, attribs)

                # transclusion is a block element
                return self.new_copy(html.div, item, attribs)

        raise RuntimeError(f"page:page need to contain exactly one page:body tag, got {elem[:]!r}")

    def visit_moinpage_part(self, elem):
        body = error = None

        for item in elem:
            if item.tag.uri == moin_page:
                if item.tag.name == "body":
                    body = item
                elif item.tag.name == "error":
                    error = item

        if body:
            # returning a Div styled like a P avoids HTML validation errors
            return self.new_copy(html.div, item, attrib={html.class_: "moin-p"})

        elif error:
            if len(error):
                ret = html.p(children=error)
            else:
                ret = html.p(children=("Error",))
            ret.set(html.class_, "moin-error")
            return ret

        # XXX: Move handling of namespace-less attributes into emeraldtree
        alt = elem.get(moin_page.alt, elem.get("alt"))
        if alt:
            return html.p(children=(alt,))

        return html.p()

    def visit_moinpage_quote(self, elem):
        return self.new_copy(html.q, elem)

    def visit_moinpage_samp(self, elem):
        return self.new_copy(html.samp, elem)

    def visit_moinpage_separator(self, elem):
        return self.new_copy(html.hr, elem)

    def visit_moinpage_span(self, elem):
        # TODO : Fix bug if a span has multiple attributes
        # Check for the attributes of span
        attrib = Attributes(elem)
        # Check for the baseline-shift (subscript or superscript)
        generate = attrib.get("baseline-shift")
        if generate:
            if generate == "sub":
                return self.new_copy(html.sub, elem)
            elif generate == "super":
                return self.new_copy(html.sup, elem)
        generate = attrib.get("font-size")
        if generate:
            if generate == "85%":
                attribute = {}
                key = html("class")
                attribute[key] = "moin-small"
                return self.new_copy(html.span, elem, attribute)
            elif generate == "120%":
                attribute = {}
                key = html("class")
                attribute[key] = "moin-big"
                return self.new_copy(html.span, elem, attribute)
        generate = attrib.get("element")
        if generate:
            if generate in self.direct_inline_tags:
                return self.new_copy(html(generate), elem)
            else:
                attribute = {}
                key = html("class")
                attribute[key] = f"element-{generate}"
                return self.new_copy(html.span, elem, attribute)
        # If no attributes are handled by our converter, just return span
        return self.new_copy(html.span, elem)

    def visit_moinpage_s(self, elem):
        return self.new_copy(html.s, elem)

    def visit_moinpage_strong(self, elem):
        return self.new_copy(html.strong, elem)

    def visit_moinpage_table(self, elem):
        attrib = Attributes(elem).convert()
        ret = html.table(attrib=attrib)
        caption = 1 if elem[0].tag.name == "caption" else 0
        for idx, item in enumerate(elem):
            tag = None
            if item.tag.uri == moin_page:
                if len(elem) > 1 + caption and html("class") in attrib and "moin-wiki-table" in attrib[html("class")]:
                    # moinwiki tables require special handling because
                    # moinwiki_in converts "||header||\n===\n||body||\n===\n||footer||" into multiple table-body's
                    if idx == 0 + caption:
                        # make first table-body after caption into header
                        tag = html.thead
                    elif len(elem) > 2 + caption and idx == len(elem) - 1:
                        # make last table-body into footer
                        tag = html.tfoot
                    else:
                        tag = html.caption if (caption and idx == 0) else html.tbody
                elif item.tag.name == "table-body":
                    tag = html.tbody
                elif item.tag.name == "table-header":
                    tag = html.thead
                elif item.tag.name == "table-footer":
                    tag = html.tfoot
                elif item.tag.name == "caption":
                    tag = html.caption
            elif item.tag.uri == html and item.tag.name in ("tbody", "thead", "tfoot"):
                tag = item.tag
            if tag is not None:
                ret.append(self.new_copy(tag, item))
        return ret

    def visit_moinpage_table_cell(self, elem):
        return self.new_copy(html.td, elem)

    def visit_moinpage_table_cell_head(self, elem):
        return self.new_copy(html.th, elem)

    def visit_moinpage_table_row(self, elem):
        return self.new_copy(html.tr, elem)

    def visit_moinpage_u(self, elem):
        return self.new_copy(html.u, elem)


class SpecialId:
    def __init__(self):
        self._ids = {}

    def gen_id(self, id):
        nr = self._ids[id] = self._ids.get(id, 0) + 1
        return nr

    def zero_id(self, id):
        self._ids[id] = 0

    def get_id(self, id):
        return self._ids.get(id, 0)

    def gen_text(self, text):
        id = wikiutil.anchor_name_from_text(text)
        nr = self._ids[id] = self._ids.get(id, 0) + 1
        if nr == 1:
            return id
        return id + f"-{nr}"


class SpecialPage:
    def __init__(self):
        self._footnotes = []
        self._headings = []
        self._tocs = []

    def add_footnote(self, elem):
        self._footnotes.append(elem)

    def remove_footnotes(self):
        self._footnotes = []

    def add_heading(self, elem, level, id=None):
        elem.append(
            html.a(attrib={html.href: f"#{id}", html.class_: "moin-permalink", html.title_: _("Link to this heading")})
        )
        self._headings.append((elem, level, id))

    def add_toc(self, elem, maxlevel):
        self._tocs.append((elem, maxlevel))

    def extend(self, page):
        self._headings.extend(page._headings)

    def footnotes(self):
        return iter(self._footnotes)

    def headings(self, maxlevel):
        minlevel = None
        for title, level, id in self._headings:
            if minlevel is None or level < minlevel:
                minlevel = level

        for elem, level, id in self._headings:
            if level > maxlevel:
                continue
            # We crop all overline levels above the first used.
            level = level - minlevel + 1
            yield elem, level, id

    def tocs(self):
        for elem, maxlevel in self._tocs:
            yield elem, self.headings(maxlevel)


class ConverterPage(Converter):
    """
    Converter application/x.moin.document -> application/x-xhtml-moin-page
    """

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, element):
        special_root = SpecialPage()
        self._special = [special_root]
        self._special_stack = [special_root]
        self._id = SpecialId()

        ret = super().__call__(element)

        special_root.root = ret

        for special in self._special:
            if special._footnotes:
                footnotes_div = self.create_footnotes(special)
                special.root.append(footnotes_div)

            for elem, headings in special.tocs():
                headings = list(headings)
                headings_list = [h[1] for h in headings]
                if headings_list:
                    maxlevel = max(headings_list)
                headtogglelink = html.a(
                    attrib={
                        html.class_: "moin-showhide",
                        html.href_: "#",
                        html.onclick_: "$('.moin-table-of-contents ol').toggle();return false;",
                    },
                    children=["[+]"],
                )
                elem_h = html.div(
                    attrib={html.class_: "moin-table-of-contents-heading"}, children=[_("Contents"), headtogglelink]
                )
                elem.append(elem_h)
                stack = [elem]

                def stack_push(elem):
                    stack[-1].append(elem)
                    stack.append(elem)

                def stack_top_append(elem):
                    stack[-1].append(elem)

                last_level = 0
                old_toggle = ""
                for elem, level, id in headings:
                    need_item = last_level >= level
                    text = "".join(elem.itertext())
                    while last_level > level:
                        stack.pop()
                        stack.pop()
                        last_level -= 1
                    while last_level < level:
                        if maxlevel != 1:
                            stack_top_append(old_toggle)
                        stack_push(html.ol())
                        stack_push(html.li({html.id_: f"li{id}"}))
                        last_level += 1
                    if need_item:
                        stack.pop()
                        stack_push(html.li({html.id_: f"li{id}"}))
                    togglelink = html.a(
                        attrib={
                            html.href_: "#",
                            html.onclick_: f"$('#li{id} ol').toggle();return false;",
                            html.class_: "moin-showhide",
                        },
                        children=["[+]"],
                    )
                    elem_a = html.a(attrib={html.href: "#" + id}, children=[text])
                    stack_top_append(elem_a)
                    old_toggle = togglelink
        return ret

    def visit(self, elem, _tag_moin_page_page_href=moin_page.page_href):
        # TODO: Is this correct, or is <page> better?
        if elem.get(_tag_moin_page_page_href):
            self._special_stack.append(SpecialPage())

            ret = super().visit(elem)

            sp = self._special_stack.pop()
            sp.root = ret
            self._special.append(sp)
            self._special_stack[-1].extend(sp)
            return ret
        else:
            return super().visit(elem)

    def visit_moinpage_h(self, elem, _tag_html_id=html.id):
        elem = super().visit_moinpage_h(elem)

        id = elem.get(_tag_html_id)
        if not id:
            id = self._id.gen_text("".join(elem.itertext()))
            elem.set(_tag_html_id, id)
        try:
            # do not create duplicate anchors to this heading when converting from one markup to another
            if not elem[-1].attrib[html.class_] == "moin-permalink":
                self._special_stack[-1].add_heading(elem, elem.level, id)
        except (AttributeError, KeyError):
            self._special_stack[-1].add_heading(elem, elem.level, id)
        return elem

    def create_footnotes(self, top):
        """Return footnotes formatted into an ET structure."""
        footnotes_div = html.div({html.class_: "moin-footnotes"})
        for elem in top.footnotes():
            footnotes_div.append(elem)
        return footnotes_div

    def visit_moinpage_note(self, elem):
        # TODO: Check note-class
        top = self._special_stack[-1]
        if len(elem) == 0:
            # explicit footnote placement:  show prior footnotes, empty stack, reset counter
            if len(top._footnotes) == 0:
                return

            footnotes_div = self.create_footnotes(top)
            top.remove_footnotes()
            self._id.zero_id("note")
            # bump note-placement counter to insure unique footnote ids
            self._id.gen_id("note-placement")
            return footnotes_div

        body = None
        for child in elem:
            if child.tag.uri == moin_page:
                if child.tag.name == "note-body":
                    body = self.do_children(child)

        id = self._id.gen_id("note")
        prefixed_id = "%s-%s" % (self._id.get_id("note-placement"), id)

        elem_ref = ET.XML(
            """
<html:sup xmlns:html="{}" html:id="note-{}-ref" html:class="moin-footnote">
<html:a html:href="#note-{}">{}</html:a>
</html:sup>
""".format(
                html, prefixed_id, prefixed_id, id
            )
        )

        elem_note = ET.XML(
            """
<html:p xmlns:html="{}" html:id="note-{}">
<html:sup><html:a html:href="#note-{}-ref">{}</html:a></html:sup>
</html:p>
""".format(
                html, prefixed_id, prefixed_id, id
            )
        )

        elem_note.extend(body)
        top.add_footnote(elem_note)

        return elem_ref

    def visit_moinpage_table_of_content(self, elem):
        try:
            level = int(elem.get(moin_page.outline_level))
            del elem.attrib[moin_page.outline_level]
        except TypeError:
            level = 6

        attribs = elem.attrib.copy()
        attribs[html.class_] = "moin-table-of-contents"
        elem = html.div(attrib=attribs)

        self._special_stack[-1].add_toc(elem, level)
        return elem


class ConverterDocument(ConverterPage):
    """
    Converter application/x.moin.document -> application/xhtml+xml
    """


default_registry.register(ConverterPage._factory, type_moin_document, Type("application/x-xhtml-moin-page"))
