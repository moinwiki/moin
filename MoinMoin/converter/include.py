# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Include handling

Expands include elements in a internal Moin document.
"""


from __future__ import absolute_import, division

from emeraldtree import ElementTree as ET
import re

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import g as flaskg

from MoinMoin import wikiutil
from MoinMoin.items import Item
from MoinMoin.util.mime import type_moin_document
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xinclude, xlink

from MoinMoin.converter.html_out import wrap_object_with_overlay
class XPointer(list):
    """
    Simple XPointer parser
    """

    tokenizer_rules = r"""
        # Match escaped syntax elements
        \^[()^]
        |
        (?P<bracket_open> \( )
        |
        (?P<bracket_close> \) )
        |
        (?P<whitespace> \s+ )
        |
        # Anything else
        [^()^]+
    """
    tokenizer_re = re.compile(tokenizer_rules, re.X)

    class Entry(object):
        __slots__ = 'name', 'data'

        def __init__(self, name, data):
            self.name, self.data = name, data

        @property
        def data_unescape(self):
            data = self.data.replace('^(', '(').replace('^)', ')')
            return data.replace('^^', '^')

    def __init__(self, input):
        name = []
        stack = []

        for match in self.tokenizer_re.finditer(input):
            if match.group('bracket_open'):
                stack.append([])
            elif match.group('bracket_close'):
                top = stack.pop()
                if stack:
                    stack[-1].append('(')
                    stack[-1].extend(top)
                    stack[-1].append(')')
                else:
                    self.append(self.Entry(''.join(name), ''.join(top)))
                    name = []
            else:
                if stack:
                    stack[-1].append(match.group())
                elif not match.group('whitespace'):
                    name.append(match.group())

        while len(stack) > 1:
            top = stack.pop()
            stack[-1].extend(top)

        if name:
            if stack:
                data = ''.join(stack.pop())
            else:
                data = None
            self.append(self.Entry(''.join(name), None))

class Converter(object):
    tag_a = moin_page.a
    tag_div = moin_page.div
    tag_h = moin_page.h
    tag_href = xlink.href
    tag_page_href = moin_page.page_href
    tag_outline_level = moin_page.outline_level
    tag_xi_href = xinclude.href
    tag_xi_include = xinclude.include
    tag_xi_xpointer = xinclude.xpointer

    @classmethod
    def _factory(cls, input, output, includes=None, **kw):
        if includes == 'expandall':
            return cls()

    def recurse(self, elem, page_href):
        # Check if we reached a new page
        page_href_new = elem.get(self.tag_page_href)
        if page_href_new:
            page_href_new = Iri(page_href_new)
            if page_href_new != page_href:
                page_href = page_href_new
                self.stack.append(page_href)
            else:
                self.stack.append(None)
        else:
            self.stack.append(None)

        try:
            if elem.tag == self.tag_xi_include:
                href = elem.get(self.tag_xi_href)
                xpointer = elem.get(self.tag_xi_xpointer)

                xp_include_pages = None
                xp_include_sort = None
                xp_include_items = None
                xp_include_skipitems = None
                xp_include_heading = None
                xp_include_level = None

                if xpointer:
                    xp = XPointer(xpointer)
                    xp_include = None
                    xp_namespaces = {}
                    for entry in xp:
                        uri = None
                        name = entry.name.split(':', 1)
                        if len(name) > 1:
                            prefix, name = name
                            uri = xp_namespaces.get(prefix, False)
                        else:
                            name = name[0]

                        if uri is None and name == 'xmlns':
                            d_prefix, d_uri = entry.data.split('=', 1)
                            xp_namespaces[d_prefix] = d_uri
                        elif uri == moin_page.namespace and name == 'include':
                            xp_include = XPointer(entry.data)

                    if xp_include:
                        for entry in xp_include:
                            name, data = entry.name, entry.data
                            if name == 'pages':
                                xp_include_pages = data
                            elif name == 'sort':
                                xp_include_sort = data
                            elif name == 'items':
                                xp_include_items = int(data)
                            elif name == 'skipitems':
                                xp_include_skipitems = int(data)
                            elif name == 'heading':
                                xp_include_heading = data
                            elif name == 'level':
                                xp_include_level = data

                if href:
                    # We have a single page to include
                    href = Iri(href)
                    link = Iri(scheme='wiki', authority='')
                    if href.scheme == 'wiki':
                        if href.authority:
                            raise ValueError("can't handle xinclude for non-local authority")
                        else:
                            path = href.path[1:]
                    elif href.scheme == 'wiki.local':
                        page = page_href
                        path = href.path
                        if path[0] == '':
                            # /subitem
                            tmp = page.path[1:]
                            tmp.extend(path[1:])
                            path = tmp
                        elif path[0] == '..':
                            # ../sisteritem
                            path = page.path[1:] + path[1:]
                    else:
                        raise ValueError("can't handle xinclude for schemes other than wiki or wiki.local")

                    link.path = path

                    page = Item.create(unicode(path))
                    pages = ((page, link), )

                elif xp_include_pages:
                    # We have a regex of pages to include
                    from MoinMoin.storage.terms import NameFn
                    inc_match = re.compile(xp_include_pages)
                    root_item = Item(name=u'')
                    pagelist = sorted([item.name for item in root_item.list_items(NameFn(inc_match))])
                    if xp_include_sort == 'descending':
                        pagelist.reverse()
                    if xp_include_skipitems is not None:
                        pagelist = pagelist[xp_include_skipitems:]
                    if xp_include_items is not None:
                        pagelist = pagelist[xp_include_items + 1:]

                    pages = ((Item.create(p), Iri(scheme='wiki', authority='', path='/' + p)) for p in pagelist)

                included_elements = []
                for page, page_href in pages:
                    if page_href in self.stack:
                        w = ('<p xmlns="%s"><strong class="error">Recursive include of "%s" forbidden</strong></p>'
                                % (html.namespace, page.name))
                        div.append(ET.XML(w))
                        continue
                    # TODO: Is this correct?
                    if not flaskg.user.may.read(page.name):
                        continue

                    if xp_include_heading is not None:
                        attrib = {self.tag_href: page_href}
                        children = (xp_include_heading or page.name, )
                        elem_a = ET.Element(self.tag_a, attrib, children=children)
                        attrib = {self.tag_outline_level: xp_include_level or '1'}
                        elem_h = ET.Element(self.tag_h, attrib, children=(elem_a, ))
                        div.append(elem_h)

                    page_doc = page.internal_representation()
                    # page_doc.tag = self.tag_div # XXX why did we have this?
                    self.recurse(page_doc, page_href)
                    # Wrap the page with the overlay, but only if it's a "page", or "a".
                    # The href needs to be an absolute URI, without the prefix "wiki://"
                    if page_doc.tag.endswith("page") or page_doc.tag.endswith("a"):
                        page_doc = wrap_object_with_overlay(page_doc, href=unicode(page_href.path))

                    included_elements.append(page_doc)

                if len(included_elements) > 1:
                    # use a div as container
                    result = ET.Element(self.tag_div)
                    result.extend(included_elements)
                elif included_elements:
                    result = included_elements[0]
                else:
                    result = None

                return result

            for i in xrange(len(elem)):
                child = elem[i]
                if isinstance(child, ET.Node):
                    ret = self.recurse(child, page_href)
                    if ret:
                        elem[i] = ret
        finally:
            self.stack.pop()

    def __call__(self, tree):
        self.stack = []

        self.recurse(tree, None)

        return tree

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, type_moin_document, type_moin_document)
