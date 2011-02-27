# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.html_in
"""


import re
import StringIO

import py.test
try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for html_in converter.")

from emeraldtree.tree import *

from MoinMoin import log
logging = log.getLogger(__name__)
from MoinMoin.converter.html_in import *

class Base(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
        html.namespace: 'html',
        xml.namespace: 'xml',
    }

    namespaces_xpath = {
        'xlink': xlink.namespace,
        'html': html.namespace,
        'xml': xml.namespace,
    }

    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input, args):
        out = self.conv(input, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces, )
        return self.output_re.sub(u'', f.getvalue())


    def do(self, input, path):
        string_to_parse = self.handle_input(input, args={})
        logging.debug("After the HTML_IN conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(path, namespaces=self.namespaces_xpath))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            ('<html><div><p>Test</p></div></html>',
             # <page><body><div><p>Test</p></div></body></page>
             '/page/body/div[p="Test"]'),
            ('<html><div><p>First paragraph</p><h1>Title</h1><p><em>Paragraph</em></p></div></html>',
             # <page><body><div><p>First paragraph</p><h outline-level="1">Title</h><p><emphasis>Paragraph</em></p></div></page></body>
             '/page/body/div/p[2][emphasis="Paragraph"]'),
            ('<html><div><p>First Line<br />Second Line</p></div></html>',
             # <page><body><div>First Line<line-break />Second Line></div></body></page>
             '/page/body/div/p[1]/line-break'),
            ('<html><div><p>First Paragraph</p><hr /><p>Second Paragraph</p></div></html>',
             # <page><body><div><p>First Paragraph</p><hr /><p>Second Paragraph</p></div></html>
             '/page/body/div/separator'),
            ('<div><p>Test</p></div>',
             # <page><body><p>Test</p></page></body>
             '/page/body[p="Test"]'),
             # Test attributes conversion
             ('<div><p class="class text" style="style text" title="title text">Test</p></div>',
             # <page><body><p html:class="class text" html:style="style text" html:title="title text">Test</p></body></page>
             '/page/body/p[@html:class="class text"][@html:style="style text"][@html:title="title text"][text()="Test"]'),
             # Test id
             ('<div><p id="first">Text<strong id="second">strong</strong></p></div>',
             # <page><body><p xml:id="first">Text<strong xml:id="second">strong</strong></p></div>
             '/page/body/p[@xml:id="first"][text()="Text"]/strong[@xml:id="second"][text()="strong"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            ('<html><h2>Test</h2></html>',
            # <page><body><h outline-level="2">Test</h></body></page>
              '/page/body/h[text()="Test"][@outline-level=2]'),
            ('<html><h6>Test</h6></html>',
            # <page><body><h outline-level="6">Test</h></body></page>
              '/page/body/h[text()="Test"][@outline-level=6]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_basic_style(self):
        data = [
            ('<html><p><em>Test</em></p></html>',
             # <page><body><p><emphasis>Test</emphasis></body></page>
              '/page/body/p[emphasis="Test"]'),
            ('<html><p><i>Test</i></p></html>',
             # <page><body><p><emphasis>Test</emphasis></body></page>
              '/page/body/p[emphasis="Test"]'),
            ('<html><p><strong>Test</strong></p></html>',
             # <page><body><p><strong>Test</strong></p></body></page>
              '/page/body/p[strong="Test"]'),
            ('<html><p><b>Test</b></p></html>',
             # <page><body><p><strong>Test</strong></p></body></page>
              '/page/body/p[strong="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span(self):
        data = [
            ('<html><p><sub>sub</sub>script</p></html>',
             # <page><body><p><span baseline-shift="sub">sub</span></p></body></page>
             '/page/body/p/span[text()="sub"][@baseline-shift="sub"]'),
            ('<html><p><sup>super</sup>script</p></html>',
             # <page><body><p><span baseline-shift="super">super</span></p></body></page>
             '/page/body/p/span[text()="super"][@baseline-shift="super"]'),
            ('<html><p><u>underline</u></p></html>',
             # <page><body><p><span text-decoration="underline">underline</span></p></body></page>
             '/page/body/p/span[text()="underline"][@text-decoration="underline"]'),
            ('<html><p><big>Test</big></p></html>',
             # <page><body><p><span font-size="120%">Test</span></p></body></page>
              '/page/body/p/span[text()="Test"][@font-size="120%"]'),
            ('<html><p><small>Test</small></p></html>',
             # <page><body><p><span font-size="85%">Test</span></p></body></page>
              '/page/body/p/span[text()="Test"][@font-size="85%"]'),
            ('<html><p><ins>underline</ins></p></html>',
             # <page><body><p><span text-decoration="underline">underline</span></p></body></page>
             '/page/body/p/span[text()="underline"][@text-decoration="underline"]'),
            ('<html><p><del>Test</del></p></html>',
             # <page><body><p><span text-decoration="line-through">Test</span></p></body></page>
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),
            ('<html><p><s>Test</s></p></html>',
             # <page><body><p><span text-decoration="line-through">Test</span></p></body></page>
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),
            ('<html><p><strike>Test</strike></p></html>',
             # <page><body><p><span text-decoration="line-through">Test</span></p></body></page>
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span_html_element(self):
        data = [
            ('<html><p><abbr>Text</abbr></p></html>',
             # <page><body><span html:class="html-abbr">Text</span></body></page>
             '/page/body/p/span[text()="Text"][@html:class="html-abbr"]'),
            ('<html><p><acronym>Text</acronym></p></html>',
             # <page><body><span html:class="html-acronym">Text</span></body></page>
             '/page/body/p/span[text()="Text"][@html:class="html-acronym"]'),
            ('<html><p><address>Text</address></p></html>',
             # <page><body><span html:class="html-address">Text</span></body></page>
             '/page/body/p/span[text()="Text"][@html:class="html-address"]'),
            ('<html><p><dfn>Text</dfn></p></html>',
             # <page><body><span html:class="html-dfn">Text</span></body></page>
             '/page/body/p/span[text()="Text"][@html:class="html-dfn"]'),
            ('<html><p><kbd>Text</kbd></p></html>',
             # <page><body><span html:class="html-kbd">Text</span></body></page>
             '/page/body/p/span[text()="Text"][@html:class="html-kbd"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            ('<html><p><a href="uri:test">Test</a></p></html>',
              # <page><body><p><a xlink:href>Test</a></p></body></page>
              '/page/body/p/a[text()="Test"][@xlink:href="uri:test"]'),
            ('<html><base href="http://www.base-url.com/" /><body><div><p><a href="myPage.html">Test</a></p></div></body></html>',
              # <page><body><div><p><a xlink:href="http://www.base-url.com/myPage.html">Test</a></p></div></body></page>
              '/page/body/div/p/a[@xlink:href="http://www.base-url.com/myPage.html"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_code(self):
        data = [
            ('<html><div><code>Code</code></div></html>',
             # <page><body><div><code>Code</code></div></body></page>
             '/page/body/div[code="Code"]'),
            ('<html><div><samp>Code</samp></div></html>',
             # <page><body><div><code>Code</code></div></body></page>
             '/page/body/div[code="Code"]'),
            ('<html><pre>Code</pre></html>',
             # <page><body><blockcode>Code</blockcode></body></page>
              '/page/body[blockcode="Code"]'),
            ('<html><p><tt>Code</tt></p></html>',
             # <page><body><p><code>Code</code></p></body></page>
              '/page/body/p[code="Code"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_quote(self):
        data = [
            ('<html><div><p><quote>Inline quote</quote></p></div></html>',
            # <page><body><div><p><quote>Inline quote</quote></p></body></page>
             '/page/body/div/p[quote="Inline quote"]'),
            ('<html><div><blockquote>Block quote</blockquote></div></html>',
            # <page><body><div><blockquote>Block quote</blockquote></body></page>
             '/page/body/div[blockquote="Block quote"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            ('<html><div><ul><li>Item</li></ul></div></html>',
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="ordered"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="A"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-alpha"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="I"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="upper-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-roman"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="a"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-alpha"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="i"><li>Item</li></ol></div></html>',
            # <page><body><div><list item-label-generate="ordered" list-style-type="lower-roman"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-roman"]/list-item[list-item-body="Item"]'),
            ('<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>',
            # <page><body><div><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></div></body></page>
             '/page/body/div/list/list-item[list-item-label="Label"][list-item-body="Item"]'),
            ('<html><div><dir><li>Item</li></dir></div></html>',
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></div></page></body></page>
              '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]'),
            ('<div><ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul></div>',
            # <page><body><div><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item><list-item><list-item-body>Item 3</list-item-body></list-item></list></div></page></body></page>
             '/page/body/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Item 1"]][list-item[2]/list-item-body[text()="Item 2"]][list-item[3]/list-item-body[text()="Item 3"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            ('<html><div><img src="uri:test" /></div></html>',
             # <page><body><div><object xlink:href="uri:test" /></div></body></page>
              '/page/body/div/object/@xlink:href="uri:test"'),
            ('<html><div><object data="href"></object></div></html>',
             # <page><body><div><object xlink:href="href" /></div></body></page>
              '/page/body/div/object/@xlink:href="href"'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            ('<html><div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div></html>',
            # <page><body><div><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></div></body></page>
             '/page/body/div/table[./table-header/table-row[table-cell="Header"]][./table-footer/table-row[table-cell="Footer"]][./table-body/table-row[table-cell="Cell"]]'),
            ('<html><div><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></div></html>',
            # <page><body><div><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>
             '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-columns-spanned="2"]'),
            ('<html><div><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></div></html>',
            # <page><body><div><table><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>
             '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-rows-spanned="2"]'),
        ]
        for i in data:
            yield (self.do, ) + i
