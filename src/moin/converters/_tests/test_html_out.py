# Copyright: 2007 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.html_out
"""

from io import StringIO

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.utils.tree import html, moin_page, xml, xlink
from moin.converters.html_out import Converter, ConverterPage, ElementException

from moin import log

logging = log.getLogger(__name__)

etree = pytest.importorskip("lxml.etree")  # noqa


class Base:
    input_namespaces = ns_all = (
        f'xmlns="{moin_page.namespace}" xmlns:page="{moin_page.namespace}" xmlns:html="{html.namespace}" xmlns:xlink="{xlink.namespace}" xmlns:xml="{xml.namespace}"'
    )
    output_namespaces = {html.namespace: "", moin_page.namespace: "page", xml.namespace: "xml"}

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        output = serialize(elem, namespaces=self.output_namespaces, **options)
        return self.output_re.sub("", output)

    def do(self, input, xpath, args={}):
        out = self.conv(self.handle_input(input), **args)
        string_to_parse = self.handle_output(out)
        logging.debug(f"After the HTML_OUT conversion : {string_to_parse}")
        tree = etree.parse(StringIO(string_to_parse))
        assert tree.xpath(xpath)


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        ("<page:page><page:body><page:p>Test</page:p></page:body></page:page>", '/div[p="Test"]'),
        ("<page:page><page:body><page:h>Test</page:h></page:body></page:page>", '/div[h1="Test"]'),
        (
            '<page:page><page:body><page:h page:outline-level="2">Test</page:h></page:body></page:page>',
            '/div[h2="Test"]',
        ),
        (
            '<page:page><page:body><page:h page:outline-level="6">Test</page:h></page:body></page:page>',
            '/div[h6="Test"]',
        ),
        (
            '<page:page><page:body><page:h page:outline-level="7">Test</page:h></page:body></page:page>',
            '/div[h6="Test"]',
        ),
        ("<page:page><page:body><page:p>Test<page:line-break/>Test</page:p></page:body></page:page>", "/div/p/br"),
        (
            "<page:page><page:body><page:p>Test<page:span>Test</page:span></page:p></page:body></page:page>",
            '/div/p[text()="Test"]/span[text()="Test"]',
        ),
        (
            "<page:page><page:body><page:p><page:emphasis>Test</page:emphasis></page:p></page:body></page:page>",
            '/div/p[em="Test"]',
        ),
        (
            "<page:page><page:body><page:p><page:strong>Test</page:strong></page:p></page:body></page:page>",
            '/div/p[strong="Test"]',
        ),
        ("<page:page><page:body><page:blockcode>Code</page:blockcode></page:body></page:page>", '/div[pre="Code"]'),
        (
            "<page:page><page:body><page:p><page:code>Code</page:code></page:p></page:body></page:page>",
            '/div/p[code="Code"]',
        ),
        ("<page:page><page:body><page:separator/></page:body></page:page>", "/div/hr"),
        (
            "<page:page><page:body><page:div><page:p>Text</page:p></page:div></page:body></page:page>",
            '/div/div[p="Text"]',
        ),
        (
            "<page:page><page:body><page:div><page:blockquote>Quotation</page:blockquote></page:div></page:body></page:page>",
            '/div/div[blockquote="Quotation"]',
        ),
        (
            "<page:page><page:body><page:div><page:p><page:quote>Quotation</page:quote></page:p></page:div></page:body></page:page>",
            '/div/div/p/q[text()="Quotation"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_base(self, input, xpath):
        self.do(input, xpath)

    data = [("<page><body /></page>", "/div"), ('<page><body class="red" /></page>', '/div[@class="red"]')]

    @pytest.mark.parametrize("input,xpath", data)
    def test_body(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Basic Links
        (
            '<page:page><page:body><page:a xlink:href="uri:test">Test</page:a></page:body></page:page>',
            '/div/a[text()="Test"][@href="uri:test"]',
        ),
        # Links with xml:base
        (
            '<page xml:base="http://base.tld/"><body><p><a xlink:href="/page.html">Test</a></p></body></page>',
            # <span xml:base="http://base.tld/"><a href="/page.html">Test</a></span>
            # TODO: commented out test below was added in 2010-08-05 bfa5c9a354b8 - seems to be no code to support
            # '/span/a[@href="http://base.tld/page.html"][text()="Test"]'),
            '/span/a[@href="/page.html"][text()="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_link(self, input, xpath):
        self.do(input, xpath)

    data = [
        # TODO: should this input work, see 5f63b38816ff 2010-06-30 and 628e532d4365 2008-06-12
        # ('<html:div html:id="a" id="b"><html:p id="c">Test</html:p></html:div>',
        ('<div html:id="a" id="b"><p id="c">Test</p></div>', '/div[@id="a"]/p[@id="c"][text()="Test"]')
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_html(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<page><body><p><inline-part><inline-body>Test</inline-body></inline-part></p></body></page>",
            '/div/p[span="Test"]',
        ),
        ('<page><body><p><inline-part alt="Alt" /></p></body></page>', '/div/p[span="Alt"]'),
        (
            "<page><body><p><inline-part><error /></inline-part></p></body></page>",
            # <div><p><span class="moin-error">Error</span></p></div>
            '/div/p/span[@class="moin-error"][text()="Error"]',
        ),
        (
            "<page><body><p><inline-part><error>Text</error></inline-part></p></body></page>",
            # <div><p><span class="moin-error">Text</span></p></div>
            '/div/p/span[@class="moin-error"][text()="Text"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_inline_part(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><p><span baseline-shift="sub">sub</span>script</p></body></page>',
            '/div/p[text()="script"][sub="sub"]',
        ),
        (
            '<page><body><p><span baseline-shift="super">super</span>script</p></body></page>',
            '/div/p[text()="script"][sup="super"]',
        ),
        ("<page><body><p><u>underline</u></p></body></page>", '/div/p/u [text()="underline"]'),
        ("<page><body><p><ins>underline</ins></p></body></page>", '/div/p/ins [text()="underline"]'),
        ("<page><body><p><s>stroke</s></p></body></page>", '/div/p/s [text()="stroke"]'),
        ("<page><body><p><del>stroke</del></p></body></page>", '/div/p/del [text()="stroke"]'),
        (
            '<page><body><p><span font-size="85%">small</span></p></body></page>',
            '/div/p/span[@class="moin-small"][text()="small"]',
        ),
        (
            '<page><body><p><span font-size="120%">big</span></p></body></page>',
            '/div/p/span[@class="moin-big"][text()="big"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_span(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ul[li="Item"]',
        ),
        (
            '<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ol[li="Item"]',
        ),
        (
            "<page><body><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></body></page>",
            '/div/dl[dt="Label"][dd="Item"]',
        ),
        (
            '<page><body><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ol[@class="moin-upperalpha-list"][li="Item"]',
        ),
        (
            '<page><body><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ol[@class="moin-loweralpha-list"][li="Item"]',
        ),
        (
            '<page><body><list item-label-generate="ordered" list-style-type="upper-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ol[@class="moin-upperroman-list"][li="Item"]',
        ),
        (
            '<page><body><list item-label-generate="ordered" list-style-type="lower-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
            '/div/ol[@class="moin-lowerroman-list"][li="Item"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_list(self, input, xpath):
        self.do(input, xpath)

    data = [
        ('<page><body><object xlink:href="href"/></body></page>', '/div/object[@data="href"]'),
        (
            '<page><body><object xlink:href="href.png" page:type="image/png"/></body></page>',
            '/div/img[@src="href.png"]',
        ),
        (
            '<page xml:base="http://base.tld/"><body><object xlink:href="href.png" page:type="image/png"/></body></page>',
            # <span xml:base="http://base.tld/"><img alt="href.png" src="href.png" /></span>
            # TODO: commented out test below was added in 2010-08-05 bfa5c9a354b8 - seems to be no code to support
            # '/span/img[@src="http://base.tld/href.png"]'),
            '/span/img[@src="href.png"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_object(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<page><body><part><body><p>Test</p></body></part></body></page>", '/div/div[p="Test"]'),
        ('<page><body><part alt="Alt" /></body></page>', '/div[p="Alt"]'),
        (
            "<page><body><part><error /></part></body></page>",
            # <div><p class="moin-error">Error</p></div>
            '/div/p[text()="Error"][@class="moin-error"]',
        ),
        (
            "<page><body><part><error>Error</error></part></body></page>",
            # <div><p class="moin-error">Error</p></div>
            '/div/p[@class="moin-error"][text()="Error"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_part(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><p style="font-size: 1em">Text</p></body></page>',
            '/div/p[@style="font-size: 1em"][text()="Text"]',
        ),
        (
            '<page><body><p style="color: black; font-size: 1em">Text</p></body></page>',
            '/div/p[@style="color: black; font-size: 1em"][text()="Text"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_style(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<page><body><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>",
            # <div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tfoot><tr><td>Cell</td></tr></tfoot></table></div>
            '/div/table[thead/tr[td="Header"]][tfoot/tr[td="Footer"]][tbody/tr[td="Cell"]]',
        ),
        (
            '<page><body><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
            '/div/table/tbody/tr/td[@colspan="2"][text()="Cell"]',
        ),
        (
            '<page><body><table><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
            '/div/table/tbody/tr/td[@rowspan="2"][text()="Cell"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_table(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><admonition page:type="warning"><p>text</p></admonition></body></page>',
            '/div/div[@class="warning"][p="text"]',
        )
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_admonition(self, input, xpath):
        self.do(input, xpath)


class TestConverterPage(Base):
    def setup_class(self):
        self.conv = ConverterPage()

    data = [
        (
            '<page><body><p>Text<note note-class="footnote"><note-body>Note</note-body></note></p></body></page>',
            # <div><p>Text<sup class="moin-footnote" id="note-0-1-ref">
            '/div[p[text()="Text"]/sup[@id="note-1-ref"]/a[@href="#note-1"][text()="1"]][p[@id="note-1"][text()="Note"]/sup/a[@href="#note-1-ref"][text()="1"]]',
        )
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_note(self, input, xpath):
        pytest.skip("this test requires footnote plugin")  # XXX TODO
        self.do(input, xpath)

    @pytest.mark.xfail
    def test_unknown(self):
        page = ET.XML(f"<page:unknown {self.input_namespaces}/>")
        pytest.raises(ElementException, self.conv.__call__, page)
