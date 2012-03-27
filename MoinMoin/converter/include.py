# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010-2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Include handling

Expands include elements in an internal Moin document.

Although this module is named include.py, many comments within and the moin docs
use the word transclude as defined by http://www.linfo.org/transclusion.html, etc.
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
from MoinMoin.items import Item
from MoinMoin.util.mime import type_moin_document
from MoinMoin.util.iri import Iri, IriPath
from MoinMoin.util.tree import html, moin_page, xinclude, xlink

from MoinMoin.converter.html_out import mark_item_as_transclusion, Attributes


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
        # on first call, elem.tag.name=='page'. Decendants (body, div, p, include, page, etc.) are processed by recursing through DOM

        # stack is used to detect transclusion loops
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
                # we have already recursed several levels and found a transclusion: "{{SomePage}}" or similar
                # process the transclusion and add it to the DOM.  Subsequent recursions will traverse through the transclusion's elements.
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
                    # We have a single page to transclude
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
                        attrib = {getattr(html, 'class'): 'moin-error'}
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

                    # if this is an existing item, mark it as a transclusion.  non-existent items are not marked (page_doc.tag.name == u'a')
                    # The href needs to be an absolute URI, without the prefix "wiki://"
                    if page_doc.tag.name == u'page':
                        page_doc = mark_item_as_transclusion(page_doc, p_href.path)
                    included_elements.append(page_doc)

                if len(included_elements) > 1:
                    # use a div as container
                    result = ET.Element(self.tag_div)
                    result.extend(included_elements)
                elif included_elements:
                    result = included_elements[0]
                else:
                    result = None
                #  end of processing for transclusion; the "result" will get inserted into the DOM below
                return result


            # Traverse the DOM by calling self.recurse with each child of the current elem.  Starting elem.tag.name=='page'.
            container = []
            i = 0
            while i < len(elem):
                child = elem[i]
                if isinstance(child, ET.Node):
                    # almost everything in the DOM will be an ET.Node, exceptions are unicode nodes under p nodes

                    ret = self.recurse(child, page_href)

                    if ret:
                        # "Normally" we are here because child.tag.name==include and ret is a transcluded item (ret.tag.name=page, image, or object, etc.)
                        # that must be inserted into the DOM replacing elem[i].
                        # This is complicated by the DOM having many inclusions, such as "\n{{SomePage}}\n" that are a child of a "p".
                        # To prevent generation of invalid HTML5 (e.g. "<p>text<p>text</p></p>"), the DOM must be adjusted.
                        if isinstance(ret, types.ListType):
                            # the transclusion may be a return of the container variable from below, add to DOM replacing the current node
                            elem[i:i+1] = ret
                        elif elem.tag.name == 'p':
                            # ancestor P nodes with tranclusions  have special case issues, we may need to mangle the ret
                            body = ret[0]
                            # check for instance where ret is a page, ret[0] a body, ret[0][0] a P
                            if not isinstance(body, unicode) and ret.tag.name == 'page' and body.tag.name == 'body' and \
                                len(body) == 1 and body[0].tag.name == 'p':
                                # special case:  "some text {{SomePage}} more text" or "\n{{SomePage}}\n" where SomePage contains a single p.
                                # the content of the transcluded P will be inserted directly into ancestor P.
                                p = body[0]
                                # get attributes from page node; we expect {class: "moin-transclusion"; data-href: "http://some.org/somepage"}
                                attrib = Attributes(ret).convert()
                                # make new span node and "convert" p to span by copying all of p's children
                                span = ET.Element(html.span, attrib=attrib, children=p[:])
                                # insert the new span into the DOM replacing old include, page, body, and p elements
                                elem[i] = span
                            elif not isinstance(body, unicode) and ret.tag.name == 'page' and body.tag.name == 'body':
                                # special case: "some text {{SomePage}} more text" or "\n{{SomePage}}\n" and SomePage body contains multiple p's, a table, preformatted text, etc.
                                # note: ancestor P may have text before or after include
                                if i > 0:
                                    # there is text before transclude, make new p node to hold text before include and save in container
                                    pa = ET.Element(html.p)
                                    pa[:] = elem[0:i]
                                    container.append(pa)
                                # get attributes from page node; we expect {class: "moin-transclusion"; data-href: "http://some.org/somepage"}
                                attrib = Attributes(ret).convert()
                                # make new div node, copy all of body's children, and save in container
                                div = ET.Element(html.div, attrib=attrib, children=body[:])
                                container.append(div)
                                 # empty elem of siblings that were just placed in container
                                elem[0:i+1] = []
                                if len(elem) > 0:
                                    # there is text after transclude, make new p node to hold text, copy siblings, save in container
                                    pa = ET.Element(html.p)
                                    pa[:] = elem[:]
                                    container.append(pa)
                                    elem[:] = []
                                # elem is now empty so while loop will terminate and container will be returned up one level in recursion
                            else:
                                # ret may be a unicode string: take default action
                                elem[i] = ret
                        else:
                            # default action for any ret not fitting special cases above
                            elem[i] = ret
                i += 1
            if len(container) > 0:
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

