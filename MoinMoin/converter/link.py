# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Link converter

Expands all links in an internal Moin document, including interwiki and
special wiki links.
"""


from __future__ import absolute_import, division

from flask import g as flaskg

from MoinMoin.util.interwiki import is_known_wiki, url_for_item
from MoinMoin.util.iri import Iri, IriPath
from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import html, moin_page, xlink, xinclude
from MoinMoin.wikiutil import AbsItemName


class ConverterBase(object):
    _tag_xlink_href = xlink.href
    _tag_xinclude_href = xinclude.href

    def handle_wiki_links(self, elem, link):
        pass

    def handle_wikilocal_links(self, elem, link, page_name):
        pass

    def handle_wiki_transclusions(self, elem, link):
        pass

    def handle_wikilocal_transclusions(self, elem, link, page_name):
        pass

    def __call__(self, *args, **kw):
        """
        Calls the self.traverse_tree method
        """
        # avoids recursion for this method
        # because it is also called in subclasses
        return self.traverse_tree(*args, **kw)

    def traverse_tree(self, elem, page=None,
            __tag_page_href=moin_page.page_href, __tag_link=_tag_xlink_href,
            __tag_include=_tag_xinclude_href):
        """
        Traverses the tree and handles each element appropriately
        """
        new_page_href=elem.get(__tag_page_href)
        if new_page_href:
            page = Iri(new_page_href)

        xlink_href = elem.get(__tag_link)
        xinclude_href = elem.get(__tag_include)
        if xlink_href:
            xlink_href = Iri(xlink_href)
            if xlink_href.scheme == 'wiki.local':
                self.handle_wikilocal_links(elem, xlink_href, page)
            elif xlink_href.scheme == 'wiki':
                self.handle_wiki_links(elem, xlink_href)
            elif xlink_href.scheme:
                elem.set(html.class_, 'moin-' + xlink_href.scheme)

        elif xinclude_href:
            xinclude_href = Iri(xinclude_href)
            if xinclude_href.scheme == 'wiki.local':
                self.handle_wikilocal_transclusions(elem, xinclude_href, page)
            elif xinclude_href.scheme == 'wiki':
                self.handle_wiki_transclusions(elem, xinclude_href)

        for child in elem.iter_elements():
            self.traverse_tree(child, page)

        return elem

    def absolute_path(self, path, current_page_path):
        """
        Converts a relative iri path into an absolute one

        :param path: the relative path to be converted
        :type path: Iri.path
        :param current_page_path: the path of the page where the link is
        :type current_page_path: Iri.path
        :returns: the absolute equivalent of the relative path
        :rtype: Iri.path
        """
        quoted_path = path.quoted
        # starts from 1 because 0 is always / for the current page
        quoted_current_page_path = current_page_path[1:].quoted

        abs_path = AbsItemName(quoted_current_page_path, quoted_path)
        abs_path = Iri(abs_path).path
        return abs_path


class ConverterExternOutput(ConverterBase):
    @classmethod
    def _factory(cls, input, output, links=None, **kw):
        if links == 'extern':
            return cls()

    def _get_do_rev(self, query):
        """
        get 'do' and 'rev' values from query string and remove them from querystring

        at the end, we translate the 'do' value to a werkzeug endpoint.

        Note: we can't use url_decode/url_encode from e.g. werkzeug because
              url_encode quotes the qs values (and Iri code will quote them again)
        """
        do = None
        revno = None
        separator = '&'
        result = []
        if query:
            for kv in query.split(separator):
                if not kv:
                    continue
                if '=' in kv:
                    k, v = kv.split('=', 1)
                else:
                    k, v = kv, ''
                if k == 'do':
                    do = v
                    continue # we remove do=xxx from qs
                if k == 'rev':
                    revno = v
                    continue # we remove rev=n from qs
                result.append(u'%s=%s' % (k, v))
        if result:
            query = separator.join(result)
        else:
            query = None
        if revno is not None:
            revno = int(revno)
        do_to_endpoint = dict(
            show='frontend.show_item',
            get='frontend.get_item',
            download='frontend.download_item',
            modify='frontend.modify_item',
            # TODO: if we just always used same function name as do=name, we did not need this dict
            # ...
        )
        endpoint = do_to_endpoint[do or 'show']
        return endpoint, revno, query

    def handle_wiki_links(self, elem, input):
        wiki_name = 'Self'
        if input.authority and input.authority.host:
            wn = unicode(input.authority.host)
            if is_known_wiki(wn):
                # interwiki link
                elem.set(html.class_, 'moin-interwiki')
                wiki_name = wn
        item_name = unicode(input.path[1:])
        endpoint, revno, query = self._get_do_rev(input.query)
        url = url_for_item(item_name, wiki_name=wiki_name, rev=revno, endpoint=endpoint)
        link = Iri(url, query=query, fragment=input.fragment)
        elem.set(self._tag_xlink_href, link)

    def handle_wikilocal_links(self, elem, input, page):
        if input.path:
            # this can be a relative path, make it absolute:
            path = input.path
            path = self.absolute_path(path, page.path)
            item_name = unicode(path)
            if not flaskg.storage.has_item(item_name):
                elem.set(html.class_, 'moin-nonexistent')
        else:
            item_name = unicode(page.path[1:])
        endpoint, revno, query = self._get_do_rev(input.query)
        url = url_for_item(item_name, rev=revno, endpoint=endpoint)
        link = Iri(url, query=query, fragment=input.fragment)
        elem.set(self._tag_xlink_href, link)


class ConverterItemRefs(ConverterBase):
    """
    determine all links and transclusions to other wiki items in this document
    """
    @classmethod
    def _factory(cls, input, output, items=None, **kw):
        if items == 'refs':
            return cls()

    def __init__(self, **kw):
        super(ConverterItemRefs, self).__init__(**kw)
        self.links = set()
        self.transclusions = set()

    def __call__(self, *args, **kw):
        """
        Refreshes the sets for links and transclusions and proxies to ConverterBase.__call__
        """
        # refreshes the sets so that we don't append to already full sets
        # in the handle methods
        self.links = set()
        self.transclusions = set()

        super(ConverterItemRefs, self).__call__(*args, **kw)

    def handle_wikilocal_links(self, elem, input, page):
        """
        Adds the link item from the input param to self.links
        :param elem: the element of the link
        :param input: the iri of the link
        :param page: the iri of the page where the link is
        """
        path = input.path
        if not path or ':' in path:
            return

        path = self.absolute_path(path, page.path)
        self.links.add(unicode(path))

    def handle_wikilocal_transclusions(self, elem, input, page):
        """
        Adds the transclusion item from input argument to self.transclusions
        :param elem: the element of the transclusion
        :param input: the iri of the transclusion
        :param page: the iri of the page where the transclusion is
        """
        path = input.path
        if not path or ':' in path:
            return

        path = self.absolute_path(path, page.path)
        self.transclusions.add(unicode(path))

    def get_links(self):
        """
        return a list of unicode link target item names
        """
        return list(self.links)

    def get_transclusions(self):
        """
        Return a list of unicode transclusion item names.
        """
        return list(self.transclusions)


from . import default_registry
default_registry.register(ConverterExternOutput._factory, type_moin_document, type_moin_document)
default_registry.register(ConverterItemRefs._factory, type_moin_document, type_moin_document)

