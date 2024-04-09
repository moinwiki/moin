# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.html_in and moin.converters.html_out.

           It will check that roundtrip conversion is working well.
"""


from io import StringIO

import pytest

from . import serialize, XMLNS_RE3

from moin.converters.html_in import Converter as HTML_IN
from moin.converters.html_out import Converter as HTML_OUT
from moin.utils.tree import html, moin_page, xlink

from moin import log

logging = log.getLogger(__name__)

etree = pytest.importorskip("lxml.etree")  # noqa


class Base:

    namespaces = {html.namespace: "", moin_page.namespace: "", xlink.namespace: "xlink"}

    output_re = XMLNS_RE3

    def handle_input(self, input, args):
        out = self.conv_html_dom(input, **args)
        output = serialize(out, namespaces=self.namespaces)
        logging.debug("After the HTML_IN conversion : {}".format(self.output_re.sub("", output)))
        out = self.conv_dom_html(out, **args)
        output = serialize(out, namespaces=self.namespaces)
        return self.output_re.sub("", output)

    def do(self, input, path):
        string_to_parse = self.handle_input(input, args={})
        logging.debug(f"After the roundtrip : {string_to_parse}")
        print("string_to_parse = %s" % string_to_parse)
        tree = etree.parse(StringIO(string_to_parse))
        assert tree.xpath(path)


class TestConverter(Base):
    def setup_class(self):
        self.conv_html_dom = HTML_IN()
        self.conv_dom_html = HTML_OUT()

    data = [
        ("<html><div><p>Test</p></div></html>", '/div/div[p="Test"]'),
        (
            "<html><div><p>First paragraph</p><h1>Title</h1><p><em>Paragraph</em></p></div></html>",
            '/div/div/p[2][em="Paragraph"]',
        ),
        ("<html><div><p>First Line<br />Second line</p></div></html>", "/div/div/p[1]/br"),
        ("<div><p>Test</p></div>", '/div/div[p="Test"]'),
        (
            '<div><p class="class" title="title">Test</p></div>',
            '/div/div/p[@class="class"][@title="title"][text()="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_base(self, input, xpath):
        self.do(input, xpath)

    data = [("<html><h2>Test</h2></html>", '/div[h2="Test"]'), ("<html><h6>Test</h6></html>", '/div[h6="Test"]')]

    @pytest.mark.parametrize("input,xpath", data)
    def test_title(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<html><p><em>Test</em></p></html>", '/div/p[em="Test"]'),
        ("<html><p><i>Test</i></p></html>", '/div/p[em="Test"]'),
        ("<html><p><strong>Test</strong></p></html>", '/div/p[strong="Test"]'),
        ("<html><p><b>Test</b></p></html>", '/div/p[strong="Test"]'),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_basic_style(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<html><p><sub>sub</sub>script</p></html>", '/div/p[sub="sub"]'),
        ("<html><p><sup>super</sup>script</p></html>", '/div/p[sup="super"]'),
        (
            "<html><p><u>underline</u></p></html>",
            # <div><p><u>underline</u></p></div>
            '/div/p/u [text()="underline"]',
        ),
        ("<html><p><big>Test</big></p></html>", '/div/p/span[@class="moin-big"][text()="Test"]'),
        ("<html><p><small>Test</small></p></html>", '/div/p/span[@class="moin-small"][text()="Test"]'),
        (
            "<html><p><ins>underline</ins></p></html>",
            # <div><p><ins>underline</ins></p></div>
            '/div/p/ins [text()="underline"]',
        ),
        ("<html><p><del>Test</del></p></html>", '/div/p[del="Test"]'),
        (
            "<html><p><s>Test</s></p></html>",
            # <div><p><s>Test</s></p></div>
            '/div/p/s [text()="Test"]',
        ),
        (
            "<html><p><strike>Test</strike></p></html>",
            # <div><p><s>Test</s></p></div>
            '/div/p/s [text()="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_span(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<html><p><abbr>Text</abbr></p></html>", '/div/p/span[@class="html-abbr"][text()="Text"]'),
        ("<html><p><acronym>Text</acronym></p></html>", '/div/p/span[@class="html-acronym"][text()="Text"]'),
        ("<html><p><address>Text</address></p></html>", '/div/p/span[@class="html-address"][text()="Text"]'),
        ("<html><p><dfn>Text</dfn></p></html>", '/div/p/span[@class="html-dfn"][text()="Text"]'),
        ("<html><p><kbd>Text</kbd></p></html>", '/div/p/span[@class="html-kbd"][text()="Text"]'),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_span_html_element(self, input, xpath):
        self.do(input, xpath)

    data = [('<html><p><a href="http:test">Test</a></p></html>', '/div/p/a[text()="Test"][@href="http:test"]')]

    @pytest.mark.parametrize("input,xpath", data)
    def test_link(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<html><div><code>Code</code></div></html>", '/div/div[code="Code"]'),
        ("<html><div><samp>Code</samp></div></html>", '/div/div[code="Code"]'),
        ("<html><pre>Code</pre></html>", '/div[pre="Code"]'),
        ("<html><p><tt>Code</tt></p></html>", '/div/p[code="Code"]'),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_code(self, input, xpath):
        self.do(input, xpath)

    data = [
        ("<html><div><ul><li>Item</li></ul></div></html>", '/div/div/ul[li="Item"]'),
        ("<html><div><ol><li>Item</li></ol></div></html>", '/div/div/ol[li="Item"]'),
        (
            '<html><div><ol type="A"><li>Item</li></ol></div></html>',
            '/div/div/ol[@class="moin-upperalpha-list"][li="Item"]',
        ),
        (
            '<html><div><ol type="I"><li>Item</li></ol></div></html>',
            '/div/div/ol[@class="moin-upperroman-list"][li="Item"]',
        ),
        (
            '<html><div><ol type="a"><li>Item</li></ol></div></html>',
            '/div/div/ol[@class="moin-loweralpha-list"][li="Item"]',
        ),
        (
            '<html><div><ol type="i"><li>Item<li></ol></div></html>',
            '/div/div/ol[@class="moin-lowerroman-list"][li="Item"]',
        ),
        ("<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>", '/div/div/dl[dt="Label"][dd="Item"]'),
        ("<html><div><dir><li>Item</li></dir></div></html>", '/div/div/ul[li="Item"]'),
        (
            "<div><ul><li>Item 1</li><p>Pouet</p><li>Item 2</li><li>Item 3</li></ul></div>",
            '/div/div/ul[li[1]="Item 1"][li[2]="Item 2"][li[3]="Item 3"]',
        ),
        # Test for bug with line return and spaces
        (
            "<div><ul><li>\n Item 1</li>\n<li>\n Item 2</li>\n<li>\n Item 3</li>\n</ul></div>",
            '/div/div/ul[li[1]="\n Item 1"][li[2]="\n Item 2"][li[3]="\n Item 3"]',
        ),
        (
            "<div><ol><li>\n Item 1</li>\n<li>\n Item 2</li>\n<li>\n Item 3</li>\n</ol></div>",
            '/div/div/ol[li[1]="\n Item 1"][li[2]="\n Item 2"][li[3]="\n Item 3"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_list(self, input, xpath):
        self.do(input, xpath)

    data = [
        # ('<html><div><img src="uri:test" /></div></html>',
        #  '/page/body/div/object/@xlink:href="uri:test"'),
        ('<html><div><object data="href"></object></div></html>', '/div/div/object[@data="href"]')
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_object(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<html><div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div></html>",
            '/div/div/table[./thead/tr[td="Header"]][./tfoot/tr[td="Footer"]][./tbody/tr[td="Cell"]]',
        ),
        (
            "<html><div><table><thead><tr><td>Header</td></tr></thead><tbody><tr><td>Cell</td></tr></tbody><tfoot><tr><td>Footer</td></tr></tfoot></table></div></html>",
            '/div/div/table[./thead/tr[td="Header"]][./tfoot/tr[td="Footer"]][./tbody/tr[td="Cell"]]',
        ),
        (
            '<html><div><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></div></html>',
            '/div/div/table/tbody/tr/td[text()="Cell"][@colspan="2"]',
        ),
        (
            '<html><div><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></div></html>',
            '/div/div/table/tbody/tr/td[text()="Cell"][@rowspan="2"]',
        ),
        # Test for bug with newline between cell
        (
            "<div><table>\n<tbody>\n<tr>\n<td>\n Cell 1:1</td>\n<td>\n Cell 1:2</td>\n</tr>\n<tr>\n<td>\n Cell 2:1</td>\n<td>\n Cell 2:2</td>\n</tr>\n</tbody>\n</table></div>",
            '/div/div/table/tbody[tr[1][td[1]="\n Cell 1:1"][td[2]="\n Cell 1:2"]][tr[2][td[1]="\n Cell 2:1"][td[2]="\n Cell 2:2"]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_table(self, input, xpath):
        self.do(input, xpath)
