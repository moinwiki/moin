# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Include handling

Expands include elements in an internal Moin document.
"""


from __future__ import absolute_import, division

from emeraldtree import ElementTree as ET
import re, types

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import g as flaskg

from whoosh.query import Term, And, Wildcard

from MoinMoin.config import NAME, NAME_EXACT, WIKINAME
from MoinMoin import wikiutil
from MoinMoin.items import Item
from MoinMoin.util.mime import type_moin_document
from MoinMoin.util.iri import Iri, IriPath
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
                            name, data = entry.name, entry.data_unescape
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
                    # XXX we currently interpret xp_include_pages as wildcard, but it should be regex
                    # for compatibility with moin 1.9. whoosh has upcoming regex support, but it is not
                    # released yet.
                    if xp_include_pages.startswith('^'):
                        # get rid of the leading ^ the Include macro needed to get into "regex mode"
                        xp_include_pages = xp_include_pages[1:]
                    query = And([Term(WIKINAME, app.cfg.interwikiname), Wildcard(NAME_EXACT, xp_include_pages)])
                    reverse = xp_include_sort == 'descending'
                    results = flaskg.storage.search(query, sortedby=NAME_EXACT, reverse=reverse, limit=None)
                    pagelist = [result[NAME] for result in results]
                    if xp_include_skipitems is not None:
                        pagelist = pagelist[xp_include_skipitems:]
                    if xp_include_items is not None:
                        pagelist = pagelist[xp_include_items + 1:]

                    pages = ((Item.create(p), Iri(scheme='wiki', authority='', path='/' + p)) for p in pagelist)

                included_elements = []
                for page, p_href in pages:
                    if p_href.path[0] != '/':
                        p_href.path = IriPath('/' + '/'.join(p_href.path))
                    if p_href in self.stack:
                        # we have a transclusion loop, create an error message showing list of pages forming loop
                        loop = self.stack[self.stack.index(p_href):]
                        loop = [u'{0}'.format(ref.path[1:]) for ref in loop if ref is not None] + [page.name]
                        msg = u'Error: Transclusion loop via: ' + u', '.join(loop)
                        attrib = {getattr(html, 'class'): 'error'}
                        strong = ET.Element(html.strong, attrib, (msg, ))
                        included_elements.append(strong)
                        continue
                    # TODO: Is this correct?
                    if not flaskg.user.may.read(page.name):
                        continue

                    if xp_include_heading is not None:
                        attrib = {self.tag_href: p_href}
                        children = (xp_include_heading or page.name, )
                        elem_a = ET.Element(self.tag_a, attrib, children=children)
                        attrib = {self.tag_outline_level: xp_include_level or '1'}
                        elem_h = ET.Element(self.tag_h, attrib, children=(elem_a, ))
                        included_elements.append(elem_h)

                    page_doc = page.internal_representation()
                    # page_doc.tag = self.tag_div # XXX why did we have this?
                    self.recurse(page_doc, page_href)
                    # Wrap the page with the overlay, but only if it's a "page", or "a".
                    # The href needs to be an absolute URI, without the prefix "wiki://"
                    if page_doc.tag.endswith("page") or page_doc.tag.endswith("a"):
                        page_doc = wrap_object_with_overlay(page_doc, href=unicode(p_href.path))

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

            container = [elem]

            i = 0
            while i < len(elem):
                child = elem[i]
                if isinstance(child, ET.Node):
                    ret = self.recurse(child, page_href)
                    if ret:
                        if type(ret) == types.ListType:
                            elem[i:i+1] = ret
                        elif elem.tag.name == 'p':
                            try:
                                body = ret[0][0]
                                if len(body) == 1 and body[0].tag.name == 'p':
                                    single = True
                                else:
                                    single = False
                            except AttributeError:
                                single = False

                            if single:
                                # content inside P is inserted directly into this P
                                p = ret[0][0][0]
                                elem[i:i+1] = [p[k] for k in xrange(len(p))]
                            else:
                                # P is closed and element is inserted after
                                pa = ET.Element(html.p)
                                pa[0:i] = elem[0:i]
                                ret[0:1] = elem[i:i+1]
                                elem[0:i+1] = []
                                container[0:0] = [pa, ret]
                                i = 0
                        else:
                            elem[i] = ret
                i += 1
            if len(container) > 1:
                return container

        finally:
            self.stack.pop()

    def __call__(self, tree):
        self.stack = []

        self.recurse(tree, None)

        return tree


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, type_moin_document, type_moin_document)

