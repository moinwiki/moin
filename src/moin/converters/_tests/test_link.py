# Copyright: 2007 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.link
"""

from emeraldtree import ElementTree as ET

from moin.converters.link import ConverterExternOutput, xlink, ConverterItemRefs
from moin.utils.iri import Iri

import pytest


@pytest.fixture
def conv():
    return ConverterExternOutput()


@pytest.mark.parametrize(
    "input_,output",
    (
        ("wiki:///Test", "/Test"),
        ("wiki:///Test:colon", "/Test:colon"),
        ("wiki:///Test?mode=raw", "/Test?mode=raw"),
        ("wiki:///Test#anchor", "/Test#anchor"),
        ("wiki:///Test?mode=raw#anchor", "/Test?mode=raw#anchor"),
        ("wiki://MoinMoin/Test", "http://moinmo.in/Test"),
    ),
)
def test_wiki(app, conv, input_, output):
    assert "MoinMoin" in app.cfg.interwiki_map

    elem = ET.Element(None)
    conv.handle_wiki_links(elem, Iri(input_))
    assert elem.get(xlink.href) == output


@pytest.mark.parametrize(
    "input_,page,output",
    (
        # note: result URLs assume test wiki running at /
        ("wiki.local:", "wiki:///Root", "/Root"),
        ("wiki.local:Test", "wiki:///Root", "/Test"),
        ("wiki.local:Test:colon", "wiki:///Root", "/Test:colon"),
        ("wiki.local:users/Test:colon", "wiki:///Root", "/users/Test:colon"),
        ("wiki.local:users:ns/Test:colon", "wiki:///Root", "/users:ns/Test:colon"),
        ("wiki.local:Test", "wiki:///Root/Sub", "/Test"),
        ("wiki.local:/Test", "wiki:///Root", "/Root/Test"),
        ("wiki.local:/Test", "wiki:///Root/Sub", "/Root/Sub/Test"),
        ("wiki.local:../Test", "wiki:///Root", "/Test"),
        ("wiki.local:../Test", "wiki:///Root/Sub", "/Root/Test"),
        # this is a local wiki item with a name happening to have a ":' inside:
        ("wiki.local:NoInterWiki:Item", "wiki:///Root", "/NoInterWiki:Item"),
    ),
)
def test_wikilocal(conv, input_, page, output):
    elem = ET.Element(None)
    conv.handle_wikilocal_links(elem, Iri(input_), Iri(page))
    assert elem.get(xlink.href) == output


@pytest.mark.parametrize(
    "input_,output",
    (("http://moinmo.in/", "http://moinmo.in/"), ("mailto:foo.bar@example.org", "mailto:foo.bar@example.org")),
)
def test_wikiexternal(conv, input_, output):
    elem = ET.Element(None)
    conv.handle_external_links(elem, Iri(input_))
    href = elem.get(xlink.href)
    assert str(href) == output


@pytest.mark.parametrize(
    "tree_xml,links_expected,transclusions_expected,external_expected",
    (
        (
            """
            <ns0:page ns0:page-href="wiki:///Home" xmlns:ns0="http://moinmo.in/namespaces/page" xmlns:ns1="http://www.w3.org/2001/XInclude" xmlns:ns2="http://www.w3.org/1999/xlink">
            <ns0:body><ns0:p><ns1:include ns1:href="wiki.local:moin_transcluded?" />
            <ns1:include ns1:href="wiki.local:moin2_transcluded?" />
            <ns0:a ns2:href="wiki.local:moin_linked">moin_linked</ns0:a>
            <ns0:a ns2:href="wiki.local:moin2_linked">moin2_linked</ns0:a></ns0:p>
            <ns0:p>safas\nafsfasfas\nfas\nfassaf</ns0:p>
            <ns0:p><ns1:include ns1:href="wiki.local:moin_transcluded?" />
            <ns1:include ns1:href="wiki.local:moin2_transcluded?" />
            <ns0:a ns2:href="wiki.local:moin_linked">moin_linked</ns0:a>
            <ns0:a ns2:href="wiki.local:moin2_linked">moin2_linked</ns0:a></ns0:p></ns0:body></ns0:page>
            """,
            ("moin_linked", "moin2_linked"),
            ("moin_transcluded", "moin2_transcluded"),
            [],
        ),
        (
            """
            <ns0:page ns0:page-href="wiki:///Home/Subpage" xmlns:ns0="http://moinmo.in/namespaces/page" xmlns:ns1="http://www.w3.org/1999/xlink" xmlns:ns2="http://www.w3.org/2001/XInclude">
            <ns0:body><ns0:p><ns0:a ns1:href="wiki.local:../../moin_linked">../../moin_linked</ns0:a>
            <ns0:a ns1:href="wiki.local:/moin2_linked">/moin2_linked</ns0:a>
            <ns2:include ns2:href="wiki.local:../../moin_transcluded?" />
            <ns2:include ns2:href="wiki.local:/moin2_transcluded?" /></ns0:p></ns0:body></ns0:page>
            """,
            ("moin_linked", "Home/Subpage/moin2_linked"),
            ("Home/Subpage/moin2_transcluded", "moin_transcluded"),
            [],
        ),
        (
            """
            <ns0:page ns0:page-href="wiki:///Home/Subpage" xmlns:ns0="http://moinmo.in/namespaces/page" xmlns:ns1="http://www.w3.org/1999/xlink" xmlns:ns2="http://www.w3.org/2001/XInclude">
            <ns0:body><ns0:p><ns0:a ns1:href="http://example.org/">test</ns0:a>
            <ns0:a ns1:href="mailto:foo.bar@example.org">test</ns0:a>
            </ns0:p></ns0:body></ns0:page>
            """,
            [],
            [],
            ("http://example.org/", "mailto:foo.bar@example.org"),
        ),
        (
            """
            <ns0:page ns0:page-href="wiki:///Home" xmlns:ns0="http://moinmo.in/namespaces/page" xmlns:ns1="http://www.w3.org/2001/XInclude" xmlns:ns2="http://www.w3.org/1999/xlink">
            <ns0:body>
            <ns0:p>
            <ns0:a ns2:href="wiki.local:NoInterWiki:Link">this is a local item not interwiki</ns0:a>
            </ns0:p>
            <ns0:p>
            <ns1:include ns1:href="wiki.local:AlsoNoInterWiki:Transclusion" />
            </ns0:p>
            </ns0:body></ns0:page>
            """,
            ("NoInterWiki:Link",),
            ("AlsoNoInterWiki:Transclusion",),
            [],
        ),
    ),
)
def test_converter_refs(tree_xml, links_expected, transclusions_expected, external_expected):
    converter = ConverterItemRefs()
    tree = ET.XML(tree_xml)

    converter(tree)
    links_result = converter.get_links()
    transclusions_result = converter.get_transclusions()
    external_result = converter.get_external_links()

    # sorting instead of sets
    # so that we avoid deduplicating duplicated items in the result
    assert sorted(links_result) == sorted(links_expected)
    assert sorted(transclusions_result) == sorted(transclusions_expected)
    assert sorted(external_result) == sorted(external_expected)
