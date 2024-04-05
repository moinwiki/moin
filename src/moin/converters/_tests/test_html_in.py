# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.html_in
"""


from io import StringIO

import pytest

from . import serialize, XMLNS_RE3

from moin.utils.tree import html, moin_page, xlink, xml
from moin.converters.html_in import Converter

from moin import log

logging = log.getLogger(__name__)

etree = pytest.importorskip("lxml.etree")  # noqa


class Base:
    namespaces = {moin_page.namespace: "", xlink.namespace: "xlink", html.namespace: "html", xml.namespace: "xml"}

    namespaces_xpath = {"xlink": xlink.namespace, "html": html.namespace, "xml": xml.namespace}

    output_re = XMLNS_RE3

    def handle_input(self, input, args):
        out = self.conv(input, **args)
        output = serialize(out, namespaces=self.namespaces)
        return self.output_re.sub("", output)

    def do(self, input, path):
        string_to_parse = self.handle_input(input, args={})
        logging.debug(f"After the HTML_IN conversion : {string_to_parse}")
        tree = etree.parse(StringIO(string_to_parse))
        print("string_to_parse = %s" % string_to_parse)
        assert tree.xpath(path, namespaces=self.namespaces_xpath)


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        (
            "<html><div><p>Test</p></div></html>",
            # <page><body><div><p>Test</p></div></body></page>
            '/page/body/div[p="Test"]',
        ),
        (
            "<html><div><p>First paragraph</p><h1>Title</h1><p><em>Paragraph</em></p></div></html>",
            # <page><body><div><p>First paragraph</p><h outline-level="1">Title</h><p><emphasis>Paragraph</em></p></div></page></body>
            '/page/body/div/p[2][emphasis="Paragraph"]',
        ),
        (
            "<html><div><p>First Line<br />Second Line</p></div></html>",
            # <page><body><div>First Line<line-break />Second Line></div></body></page>
            "/page/body/div/p[1]/line-break",
        ),
        (
            "<html><div><p>First Paragraph</p><hr /><p>Second Paragraph</p></div></html>",
            # <page><body><div><p>First Paragraph</p><hr /><p>Second Paragraph</p></div></html>
            "/page/body/div/separator",
        ),
        (
            "<div><p>Test</p></div>",
            # <page><body><div><p>Test</p></div></body></page>
            '/page/body/div[p="Test"]',
        ),
        # Test attributes conversion
        (
            '<div><p class="class text" style="style text" title="title text">Test</p></div>',
            # <page><body><div><p html:class="class text" html:style="style text" html:title="title text">Test</p></div></body></page>
            '/page/body/div/p[@html:class="class text"][@html:style="style text"][@html:title="title text"][text()="Test"]',
        ),
        # Test id
        (
            '<div><p id="first">Text<strong id="second">strong</strong></p></div>',
            # <page><body><div><p xml:id="first">Text<strong xml:id="second">strong</strong></p></div></body></page>
            '/page/body/div/p[@xml:id="first"][text()="Text"]/strong[@xml:id="second"][text()="strong"]',
        ),
        # test trailing div part 1
        (
            "<p>Paragraph</p><div>Div</div>",
            # <page><body><p>paragraph</p><div>div</div></body></page>
            '/page/body[p="Paragraph"]',
        ),
        # test trailing div part 2
        (
            "<p>Paragraph</p><div>Div</div>",
            # <page><body><p>paragraph</p><div>div</div></body></page>
            '/page/body/div/text()="Div"',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_base(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><h2>Test</h2></html>",
            # <page><body><h outline-level="2">Test</h></body></page>
            '/page/body/h[text()="Test"][@outline-level=2]',
        ),
        (
            "<html><h6>Test</h6></html>",
            # <page><body><h outline-level="6">Test</h></body></page>
            '/page/body/h[text()="Test"][@outline-level=6]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_title(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><p><em>Test</em></p></html>",
            # <page><body><p><emphasis>Test</emphasis></body></page>
            '/page/body/p[emphasis="Test"]',
        ),
        (
            "<html><p><i>Test</i></p></html>",
            # <page><body><p><emphasis>Test</emphasis></body></page>
            '/page/body/p[emphasis="Test"]',
        ),
        (
            "<html><p><strong>Test</strong></p></html>",
            # <page><body><p><strong>Test</strong></p></body></page>
            '/page/body/p[strong="Test"]',
        ),
        (
            "<html><p><b>Test</b></p></html>",
            # <page><body><p><strong>Test</strong></p></body></page>
            '/page/body/p[strong="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_basic_style(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><p><sub>sub</sub>script</p></html>",
            # <page><body><p><span baseline-shift="sub">sub</span></p></body></page>
            '/page/body/p/span[text()="sub"][@baseline-shift="sub"]',
        ),
        (
            "<html><p><sup>super</sup>script</p></html>",
            # <page><body><p><span baseline-shift="super">super</span></p></body></page>
            '/page/body/p/span[text()="super"][@baseline-shift="super"]',
        ),
        (
            "<html><p><u>underline</u></p></html>",
            # <page><body><p><u>underline</u></p></body></page>
            '/page/body/p/u[text()="underline"]',
        ),
        (
            "<html><p><big>Test</big></p></html>",
            # <page><body><p><span font-size="120%">Test</span></p></body></page>
            '/page/body/p/span[text()="Test"][@font-size="120%"]',
        ),
        (
            "<html><p><small>Test</small></p></html>",
            # <page><body><p><span font-size="85%">Test</span></p></body></page>
            '/page/body/p/span[text()="Test"][@font-size="85%"]',
        ),
        (
            "<html><p><ins>underline</ins></p></html>",
            # <page><body><p><ins>underline</ins></p></body></page>
            '/page/body/p/ins[text()="underline"]',
        ),
        (
            "<html><p><del>Test</del></p></html>",
            # <page><body><p><del>Test</del></p></body></page>
            '/page/body/p/del[text()="Test"]',
        ),
        (
            "<html><p><s>Test</s></p></html>",
            # <page><body><p><s>Test</s></p></body></page>
            '/page/body/p/s[text()="Test"]',
        ),
        (
            "<html><p><strike>Test</strike></p></html>",
            # <page><body><p><s>Test</s></p></body></page>
            '/page/body/p/s[text()="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_span(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><p><abbr>Text</abbr></p></html>",
            # <page><body><span html:class="html-abbr">Text</span></body></page>
            '/page/body/p/span[text()="Text"][@html:class="html-abbr"]',
        ),
        (
            "<html><p><acronym>Text</acronym></p></html>",
            # <page><body><span html:class="html-acronym">Text</span></body></page>
            '/page/body/p/span[text()="Text"][@html:class="html-acronym"]',
        ),
        (
            "<html><p><address>Text</address></p></html>",
            # <page><body><span html:class="html-address">Text</span></body></page>
            '/page/body/p/span[text()="Text"][@html:class="html-address"]',
        ),
        (
            "<html><p><dfn>Text</dfn></p></html>",
            # <page><body><span html:class="html-dfn">Text</span></body></page>
            '/page/body/p/span[text()="Text"][@html:class="html-dfn"]',
        ),
        (
            "<html><p><kbd>Text</kbd></p></html>",
            # <page><body><span html:class="html-kbd">Text</span></body></page>
            '/page/body/p/span[text()="Text"][@html:class="html-kbd"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_span_html_element(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<html><p><a href="http:test">Test</a></p></html>',
            # <page><body><p><a xlink:href="http:test">Test</a></p></body></page>
            '/page/body/p/a[text()="Test"][@xlink:href="http:test"]',
        ),
        (
            '<html><base href="http://www.base-url.com/" /><body><div><p><a href="myPage.html">Test</a></p></div></body></html>',
            # <page><body><div><p><a xlink:href="http://www.base-url.com/myPage.html">Test</a></p></div></body></page>
            '/page/body/div/p/a[@xlink:href="http://www.base-url.com/myPage.html"]',
        ),
        # verify invalid or forbidden uri schemes are removed
        (
            """<html><p><a href="javascript:alert('hi')">Test</a></p></html>""",
            # <page><body><p>javascript:alert('hi')</p></body></page>
            """/page/body/p[text()="javascript:alert('hi')"]""",
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_link(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><div><code>Code</code></div></html>",
            # <page><body><div><code>Code</code></div></body></page>
            '/page/body/div[code="Code"]',
        ),
        (
            "<html><div><samp>Code</samp></div></html>",
            # <page><body><div><code>Code</code></div></body></page>
            '/page/body/div[code="Code"]',
        ),
        (
            "<html><pre>Code</pre></html>",
            # <page><body><blockcode>Code</blockcode></body></page>
            '/page/body[blockcode="Code"]',
        ),
        (
            "<html><p><tt>Code</tt></p></html>",
            # <page><body><p><code>Code</code></p></body></page>
            '/page/body/p[code="Code"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_code(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><div><p><quote>Inline quote</quote></p></div></html>",
            # <page><body><div><p><quote>Inline quote</quote></p></body></page>
            '/page/body/div/p[quote="Inline quote"]',
        ),
        (
            "<html><div><blockquote>Block quote</blockquote></div></html>",
            # <page><body><div><blockquote>Block quote</blockquote></body></page>
            '/page/body/div[blockquote="Block quote"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_quote(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><div><ul><li>Item</li></ul></div></html>",
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]',
        ),
        (
            "<html><div><ol><li>Item</li></ol></div></html>",
            # <page><body><div><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="ordered"]/list-item[list-item-body="Item"]',
        ),
        (
            '<html><div><ol type="A"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-alpha"]/list-item[list-item-body="Item"]',
        ),
        (
            '<html><div><ol type="I"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="upper-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-roman"]/list-item[list-item-body="Item"]',
        ),
        (
            '<html><div><ol type="a"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-alpha"]/list-item[list-item-body="Item"]',
        ),
        (
            '<html><div><ol type="i"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="lower-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-roman"]/list-item[list-item-body="Item"]',
        ),
        (
            "<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>",
            # <page><body><div><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list/list-item[list-item-label="Label"][list-item-body="Item"]',
        ),
        (
            "<html><div><dir><li>Item</li></dir></div></html>",
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]',
        ),
        (
            "<div><ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul></div>",
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item><list-item><list-item-body>Item 3</list-item-body></list-item></list></div></page></body></page>
            '/page/body/div/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Item 1"]][list-item[2]/list-item-body[text()="Item 2"]][list-item[3]/list-item-body[text()="Item 3"]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_list(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<html><div><img src="uri:test" /></div></html>',
            # <page><body><div><object xlink:href="uri:test" /></div></body></page>
            '/page/body/div/object/@xlink:href="uri:test"',
        ),
        (
            '<html><div><object data="href"></object></div></html>',
            # <page><body><div><object xlink:href="href" /></div></body></page>
            '/page/body/div/object/@xlink:href="href"',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_object(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div></html>",
            # <page><body><div><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></div></body></page>
            '/page/body/div/table[./table-header/table-row[table-cell="Header"]][./table-footer/table-row[table-cell="Footer"]][./table-body/table-row[table-cell="Cell"]]',
        ),
        (
            '<html><div><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></div></html>',
            # <page><body><div><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>
            '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-columns-spanned="2"]',
        ),
        (
            '<html><div><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></div></html>',
            # <page><body><div><table><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>
            '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-rows-spanned="2"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_table(self, input, xpath):
        self.do(input, xpath)
