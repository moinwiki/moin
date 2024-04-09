# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Image converter

Convert image to <object> tag for the DOM Tree.
"""

from urllib.parse import urlencode, parse_qs

from moin.constants.contenttypes import CHARSET
from moin.utils.iri import Iri
from moin.utils.mime import Type, type_moin_document
from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.constants.keys import SUMMARY

from . import default_registry


class Converter:
    """
    Convert an image to the corresponding <object> in the DOM Tree
    """

    @classmethod
    def _factory(cls, input, output, **kw):
        return cls(input_type=input)

    def __init__(self, input_type):
        self.input_type = input_type

    def __call__(self, rev, contenttype=None, arguments=None):
        item_name = rev.item.name
        query_keys = {"do": "get", "rev": rev.revid}
        attrib = {}
        if arguments:
            query = arguments.keyword.get(xinclude.href)
            if query and query.query:
                # query.query value is similar to  "w=75" given a transclusion "{{jpeg||&w=75 class="top"}}"
                query_keys.update(parse_qs(query.query))
            attrib = arguments.keyword

        query = urlencode(query_keys, encoding=CHARSET)

        attrib.update(
            {
                moin_page.type_: str(self.input_type),
                xlink.href: Iri(scheme="wiki", authority="", path="/" + rev.item.fqname.fullname, query=query),
            }
        )
        if rev.meta.get(SUMMARY) and html.alt not in attrib:
            attrib[html.alt] = rev.meta[SUMMARY]

        obj = moin_page.object_(attrib=attrib, children=[item_name])
        body = moin_page.body(children=(obj,))
        return moin_page.page(children=(body,))


default_registry.register(Converter._factory, Type("image/svg+xml"), type_moin_document)
default_registry.register(Converter._factory, Type("image/png"), type_moin_document)
default_registry.register(Converter._factory, Type("image/jpeg"), type_moin_document)
default_registry.register(Converter._factory, Type("image/gif"), type_moin_document)
