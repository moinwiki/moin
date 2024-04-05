# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.docbook_out
"""

from io import StringIO

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE3, TAGSTART_RE

from moin.utils.tree import html, moin_page, xlink, xml, docbook
from moin.converters.docbook_out import Converter

from moin import log

logging = log.getLogger(__name__)

etree = pytest.importorskip("lxml.etree")  # noqa


class Base:
    input_namespaces = ns_all = (
        f'xmlns="{moin_page.namespace}" xmlns:page="{moin_page.namespace}" xmlns:html="{html.namespace}" xmlns:xlink="{xlink.namespace}" xmlns:xml="{xml.namespace}"'
    )
    output_namespaces = {
        docbook.namespace: "",
        moin_page.namespace: "page",
        xlink.namespace: "xlink",
        xml.namespace: "xml",
    }

    namespaces_xpath = {"xlink": xlink.namespace, "xml": xml.namespace}

    input_re = TAGSTART_RE
    output_re = XMLNS_RE3

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        output = serialize(elem, namespaces=self.output_namespaces, **options)
        return self.output_re.sub("", output)

    def do(self, input, xpath, args={}):
        out = self.conv(self.handle_input(input), **args)
        string_to_parse = self.handle_output(out)
        logging.debug(f"After the docbook_OUT conversion : {string_to_parse}")
        tree = etree.parse(StringIO(string_to_parse))
        assert tree.xpath(xpath, namespaces=self.namespaces_xpath)


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        # NB: All the output contain the <info> section, but for a better
        #     readability, I did not wrote it in the snippet except this one
        (
            "<page><body><p>Test</p></body></page>",
            # <article><info><title>Untitled</title></info><simpara>Test</simpara></article>
            '/article[./info[title="Untitled"]][simpara="Test"]',
        ),
        # ADMONITION type --> type
        (
            '<page><body><admonition page:type="warning"><p>Text</p></admonition></body></page>',
            # <article><warning><simpara>Text</simpara></warning></article>
            '/article/warning[simpara="Text"]',
        ),
        # Unknown admonition
        ('<page><body><admonition page:type="none"><p>Text</p></admonition></body></page>', '/article[simpara="Text"]'),
        # XML attributes: we support all the xml standard attributes
        (
            '<page><body><p xml:base="http://base.tld" xml:id="id" xml:lang="en">Text</p></body></page>',
            # <article><simpara xml:base="http://base.tld" xml:id="id" xml:lang="en">Text</p></body></page>
            '/article/simpara[@xml:base="http://base.tld"][@xml:id="id"][@xml:lang="en"][text()="Text"]',
        ),
        # Para with title
        (
            '<page><body><p html:title="Title">Text</p></body></page>',
            # <article><simpara xml:base="http://base.tld" xml:id="id" xml:lang="en">Text</p></body></page>
            '/article/para[text()="Text"][title="Title"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_base(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><h page:outline-level="1">Heading 1</h><p>First</p><h page:outline-level="2">Heading 2</h><p>Second</p></body></page>',
            '/article/sect1[title="Heading 1"][simpara="First"]/sect2[title="Heading 2"][simpara="Second"]',
        )
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_title(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Simple unordered list
        (
            '<page><body><list page:item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><itemizedlist><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></itemizedlist></article>
            '/article/itemizedlist[listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple ordered list (use default arabic numeration)
        (
            '<page><body><list page:item-label-generate="ordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><orderedlist numeration="arabic"><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></orderedlist></article>
            '/article/orderedlist[@numeration="arabic"][listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple ordered list with upper-alpha numeration
        (
            '<page><body><list page:item-label-generate="ordered" page:list-style-type="upper-alpha"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><orderedlist numeration="upperalpha"><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></orderedlist></article>
            '/article/orderedlist[@numeration="upperalpha"][listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple ordered list with lower-alpha numeration
        (
            '<page><body><list page:item-label-generate="ordered" page:list-style-type="lower-alpha"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><orderedlist numeration="loweralpha"><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></orderedlist></article>
            '/article/orderedlist[@numeration="loweralpha"][listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple ordered list with upper-roman numeration
        (
            '<page><body><list page:item-label-generate="ordered" page:list-style-type="upper-roman"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><orderedlist numeration="upperroman"><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></orderedlist></article>
            '/article/orderedlist[@numeration="upperroman"][listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple ordered list with lower-roman numeration
        (
            '<page><body><list page:item-label-generate="ordered" page:list-style-type="lower-roman"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
            # <article><orderedlist numeration="lowerroman"><listitem><simpara>Item 1</simpara></listitem><listitem><simpara>Item 2</simpara></listitem></orderedlist></article>
            '/article/orderedlist[@numeration="lowerroman"][listitem[1]/simpara[text()="Item 1"]][listitem[2]/simpara[text()="Item 2"]]',
        ),
        # Simple definition list
        (
            "<page><body><list><list-item><list-item-label>First Term</list-item-label><list-item-body>First Definition</list-item-body></list-item><list-item><list-item-label>Second Term</list-item-label><list-item-body>Second Definition</list-item-body></list-item></list></body></page>",
            # <article><variablelist><varlistentry><term>First Term</term><listitem><simpara>First Definition</simpara></listitem></varlistentry><varlistentry><term>Second term</term><listitem><simpara>Second Definition</simpara></listitem></varlistentry></variablelist></article>
            '/article/variablelist[varlistentry[1][./term[text()="First Term"]][./listitem/simpara[text()="First Definition"]]][varlistentry[2][./term[text()="Second Term"]][./listitem/simpara[text()="Second Definition"]]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_list(self, input, xpath):
        self.do(input, xpath)

    data = [
        # All the table output caption, just wrote a test and snippet
        # for the two first tests.
        (
            "<page><body><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>",
            # <article><table><caption>Table 0</caption><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table>
            '/article/table[caption="Table 0"][thead/tr[td="Header"]][tfoot/tr[td="Footer"]][tbody/tr[td="Cell"]]',
        ),
        (
            '<page><body><table html:title="Title"><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
            # <article><table><caption>Title</caption><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table>
            '/article/table[caption="Title"][thead/tr[td="Header"]][tfoot/tr[td="Footer"]][tbody/tr[td="Cell"]]',
        ),
        (
            '<page><body><table><table-body><table-row><table-cell page:number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
            # <article><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></article>
            '/article/table/tbody/tr/td[@colspan="2"][text()="Cell"]',
        ),
        (
            '<page><body><table><table-body><table-row><table-cell page:number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
            # <article><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></article>
            '/article/table/tbody/tr/td[@rowspan="2"][text()="Cell"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_table(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Footnote conversion
        (
            '<page><body><p>Text simpara<note page:note-class="footnote"><note-body>Text Footnote</note-body></note></p></body></page>',
            # <article><simpara>Text simpara<footnote>Text Footnote</footnote></simpara></article>
            '/article/simpara[text()="Text simpara"]/footnote[simpara="Text Footnote"]',
        ),
        # Link conversion
        (
            '<page><body><p><a xlink:href="uri:test" xlink:title="title">link</a></p></body></page>',
            # <article><simpara><link xlink:href="uri:test" xlink:title="title">link</link></simpara></article>
            '/article/simpara/link[@xlink:href="uri:test"][@xlink:title="title"][text()="link"]',
        ),
        # Blockcode conversion into <screen> with CDATA
        (
            "<page><body><blockcode>Text</blockcode></body></page>",
            # <article><screen><![CDATA[Text]]></screen></article>
            '/article[screen="<![CDATA[Text]]>"]',
        ),
        # Code conversion into <literal>
        (
            "<page><body><p><code>Text</code></p></body></page>",
            # <article><simpara><literal>Text</literal></simpara></article>
            '/article/simpara[literal="Text"]',
        ),
        # SPAN --> PHRASE
        (
            "<page><body><p><span>Text</span></p></body></page>",
            # <article><simpara><phrase>Text</phrase></simpara></article>
            '/article/simpara[phrase="Text"]',
        ),
        # SPAN baseline-shift=sub --> subscript
        (
            '<page><body><p>sub<span page:baseline-shift="sub">sub</span>script</p></body></page>',
            # <article><simpara>script<subscript>sub</subscript></simpara></article>
            '/article/simpara[text()="script"][subscript="sub"]',
        ),
        # SPAN baseline-shift=super --> superscript
        (
            '<page><body><p>sub<span page:baseline-shift="super">super</span>script</p></body></page>',
            # <article><simpara>script</simpara><superscript>super</superscript></article>
            '/article/simpara[text()="script"][superscript="super"]',
        ),
        # STRONG --> EMPHASIS role='strong'
        (
            "<page><body><p>text<strong>strong</strong></p></body></page>",
            # <article><simpara>text<emphasis role="strong">strong</emphasis></simpara>
            '/article/simpara[text()="text"]/emphasis[@role="strong"][text()="strong"]',
        ),
        # EMPHASIS --> EMPHASIS
        (
            "<page><body><p>text<emphasis>emphasis</emphasis></p></body></page>",
            # <article><simpara>text<emphasis>emphasis</emphasis></simpara>
            '/article/simpara[text()="text"][emphasis="emphasis"]',
        ),
        # LINE-BREAK --> SBR
        (
            "<page><body><p>Line 1<line-break />Line 2</p></body></page>",
            # <article><simpara>Line 1<sbr />Line 2</simpara></article>
            '/article/simpara[text()="Line 1"]/sbr',
        ),
        # QUOTE --> QUOTE
        (
            "<page><body><p>Text<quote>quotation</quote></p></body></page>",
            # <article><simpara>Text<quote>quotation</quote></simpara></body></page>
            '/article/simpara[text()="Text"][quote="quotation"]',
        ),
        # BLOCKQUOTE --> BLOCKQUOTE
        (
            '<page><body><blockquote page:source="Socrates">One thing only I know, and that is that I know nothing.</blockquote></body></page>',
            # <article><blockquote><attribution>Socrates</attribution><simpara>One thing ... nothing</simpara></blockquote></article>
            '/article/blockquote[attribution="Socrates"][simpara="One thing only I know, and that is that I know nothing."]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_simparagraph_elements(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<page><body><p><object xlink:href="pics.png" page:type="image/" /></p></body></page>',
            # <article><simpara><inlinemediaobject><imageobject><imagedata fileref="pics.png"></imageobject></inlinemediaobject></simpara></article>
            '/article/simpara/inlinemediaobject/imageobject/imagedata[@fileref="pics.png"]',
        ),
        (
            '<page><body><p><object xlink:href="sound.wav" page:type="audio/" /></p></body></page>',
            # <article><simpara><inlinemediaobject><audioobject><audiodata fileref="sound.wav"></audioobject></inlinemediaobject></simpara></article>
            '/article/simpara/inlinemediaobject/audioobject/audiodata[@fileref="sound.wav"]',
        ),
        (
            '<page><body><p><object xlink:href="video.ogg" page:type="video/" /></p></body></page>',
            # <article><simpara><inlinemediaobject><videoobject><videodata fileref="video.ogg"></videoobject></inlinemediaobject></simpara></article>
            '/article/simpara/inlinemediaobject/videoobject/videodata[@fileref="video.ogg"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_object(self, input, xpath):
        self.do(input, xpath)
