# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Link converter

Expands all links in an internal Moin document, including interwiki and
special wiki links.
"""

from flask import current_app as app
from flask import g as flaskg

from moin.constants.misc import VALID_ITEMLINK_VIEWS
from moin.utils.interwiki import is_known_wiki, url_for_item
from moin.utils.iri import Iri
from moin.utils.mime import type_moin_document
from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.wikiutil import AbsItemName

from . import default_registry


class ConverterBase:
    _tag_xlink_href = xlink.href
    _tag_xinclude_href = xinclude.href
    _tag_html_data_href = html.data_href

    def handle_wiki_links(self, elem, link, to_tag=_tag_xlink_href):
        pass

    def handle_wikilocal_links(self, elem, link, page_name, to_tag=_tag_xlink_href):
        pass

    def handle_wiki_transclusions(self, elem, link):
        pass

    def handle_wikilocal_transclusions(self, elem, link, page_name):
        pass

    def handle_external_links(self, elem, link, to_tag=_tag_xlink_href):
        pass

    def __call__(self, *args, **kw):
        """
        Calls the self.traverse_tree method
        """
        # avoids recursion for this method
        # because it is also called in subclasses
        return self.traverse_tree(*args, **kw)

    def traverse_tree(
        self,
        elem,
        page=None,
        __tag_page_href=moin_page.page_href,
        __tag_link=_tag_xlink_href,
        __tag_include=_tag_xinclude_href,
        __tag_data_href=_tag_html_data_href,
    ):
        """
        Traverses the tree and handles each element appropriately
        """
        new_page_href = elem.get(__tag_page_href)
        if new_page_href:
            page = Iri(new_page_href)

        xlink_href = elem.get(__tag_link)
        xinclude_href = elem.get(__tag_include)
        data_href = elem.get(__tag_data_href)
        for href, to_tag in (xlink_href, self._tag_xlink_href), (data_href, self._tag_html_data_href):
            if href:
                href = Iri(href)
                if href.scheme == "wiki.local":
                    self.handle_wikilocal_links(elem, href, page, to_tag)
                elif href.scheme == "wiki":
                    self.handle_wiki_links(elem, href, to_tag)
                elif href.scheme:
                    self.handle_external_links(elem, href, to_tag)

        if not xlink_href and xinclude_href:
            xinclude_href = Iri(xinclude_href)
            if xinclude_href.scheme == "wiki.local":
                self.handle_wikilocal_transclusions(elem, xinclude_href, page)
            elif xinclude_href.scheme == "wiki":
                self.handle_wiki_transclusions(elem, xinclude_href)

        elif xlink_href == "":
            # reST link to page fragment
            elem.set(self._tag_xlink_href, "#" + elem.text.replace(" ", "_"))

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
        if quoted_path.startswith("/"):
            # avoid Iri issue where item name containing a colon is mistaken for scheme:path
            abs_path = Iri(path=abs_path).path
        return abs_path


class ConverterExternOutput(ConverterBase):
    @classmethod
    def _factory(cls, input, output, links=None, **kw):
        if links == "extern":
            return cls()

    def _get_do_rev(self, query):
        """
        get 'do' and 'rev' values from query string and remove them from querystring

        at the end, we translate the 'do' value to a werkzeug endpoint.

        Note: we can't use url_decode/url_encode from e.g. werkzeug because
              url_encode quotes the qs values (and Iri code will quote them again)
        """
        do = None
        rev = None
        separator = "&"
        result = []
        if query:
            for kv in query.split(separator):
                if not kv:
                    continue
                if "=" in kv:
                    k, v = kv.split("=", 1)
                else:
                    k, v = kv, ""
                if k == "do":
                    do = v
                    continue  # we remove do=xxx from qs
                if k == "rev":
                    rev = v
                    continue  # we remove rev=n from qs
                result.append(f"{k}={v}")
        if result:
            query = separator.join(result)
        else:
            query = None
        do_to_endpoint = dict(
            show="frontend.show_item",
            get="frontend.get_item",
            download="frontend.download_item",
            modify="frontend.modify_item",
            # TODO: if we just always used same function name as do=name, we did not need this dict
            # ...
        )
        endpoint = do_to_endpoint[do or "show"]
        return endpoint, rev, query

    def handle_wiki_links(self, elem, input, to_tag=ConverterBase._tag_xlink_href):
        wiki_name = "Self"
        if input.authority and input.authority.host:
            wn = str(input.authority.host)
            if is_known_wiki(wn):
                # interwiki link
                if html.class_ in elem.attrib:
                    elem.set(moin_page.class_, "moin-interwiki " + elem.attrib[html.class_])
                else:
                    elem.set(moin_page.class_, "moin-interwiki")
                wiki_name = wn
                elem.set(moin_page.title_, wn)
        item_name = str(input.path[1:])
        endpoint, rev, query = self._get_do_rev(input.query)
        url = url_for_item(item_name, wiki_name=wiki_name, rev=rev, endpoint=endpoint)
        link = Iri(url, query=query, fragment=input.fragment)
        elem.set(to_tag, link)

    def handle_wikilocal_links(self, elem, input, page, to_tag=ConverterBase._tag_xlink_href):
        view_name = ""
        if input.path:
            item_name = str(input.path)
            # Remove view from item_name before searching
            if item_name.startswith("+"):
                view_name = item_name.split("/")[0]
                if view_name in VALID_ITEMLINK_VIEWS:
                    item_name = item_name.split(f"{view_name}/")[1]
            if page:
                # this can be a relative path, make it absolute:
                item_name = str(self.absolute_path(Iri(path=item_name).path, page.path))
            if not flaskg.storage.has_item(item_name):
                # XXX these index accesses slow down the link converter quite a bit
                elem.set(moin_page.class_, "moin-nonexistent")
        else:
            item_name = str(page.path[1:]) if page else ""
        endpoint, rev, query = self._get_do_rev(input.query)

        if view_name in app.view_endpoints.keys():
            # Other views will be shown with class moin-nonexistent as non-existent links
            endpoint = app.view_endpoints[view_name]

        url = url_for_item(item_name, rev=rev, endpoint=endpoint)
        if not page:
            url = url[1:]
        link = Iri(url, query=query, fragment=input.fragment)
        elem.set(to_tag, link)

    def handle_external_links(self, elem, input, to_tag=ConverterBase._tag_xlink_href):
        elem.set(to_tag, input)
        # rst_in.py may create a link similar to "http:Home", we check input.authority to verify link is external
        if elem.tag == moin_page.a and input.authority:
            # adding this class enables themes to flag external links with an icon
            elem.set(html.class_, elem.attrib.get(html.class_, "") + " moin-" + input.scheme)


class ConverterItemRefs(ConverterBase):
    """
    determine all links and transclusions to other wiki items in this document
    """

    @classmethod
    def _factory(cls, input, output, items=None, **kw):
        if items == "refs":
            return cls()

    def __init__(self, **kw):
        super().__init__(**kw)
        self.links = set()
        self.transclusions = set()
        self.external_links = set()

    def __call__(self, *args, **kw):
        """
        Refreshes the sets for links and transclusions and proxies to ConverterBase.__call__
        """
        # refreshes the sets so that we don't append to already full sets
        # in the handle methods
        self.links = set()
        self.transclusions = set()
        self.external_links = set()

        super().__call__(*args, **kw)

    def handle_wikilocal_links(self, elem, input, page, to_tag=ConverterBase._tag_xlink_href):
        """
        Adds the link item from the input param to self.links
        :param elem: the element of the link
        :param input: the iri of the link
        :param page: the iri of the page where the link is
        """
        path = input.path
        if not path or ":" in path:
            return

        path = self.absolute_path(path, page.path)
        self.links.add(str(path))

    def handle_wikilocal_transclusions(self, elem, input, page):
        """
        Adds the transclusion item from input argument to self.transclusions
        :param elem: the element of the transclusion
        :param input: the iri of the transclusion
        :param page: the iri of the page where the transclusion is
        """
        path = input.path
        if not path or ":" in path:
            return

        path = self.absolute_path(path, page.path)
        self.transclusions.add(str(path))

    def handle_external_links(self, elem, input, to_tag=ConverterBase._tag_xlink_href):
        """
        Adds the link item from the input param to self.external_links
        :param elem: the element of the link
        :param input: the iri of the link
        """
        self.external_links.add(str(input))

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

    def get_external_links(self):
        """
        return a list of unicode external links target item names
        """
        return list(self.external_links)


default_registry.register(ConverterExternOutput._factory, type_moin_document, type_moin_document)
default_registry.register(ConverterItemRefs._factory, type_moin_document, type_moin_document)
