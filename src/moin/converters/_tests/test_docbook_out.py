# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.converters.docbook_out tests.
"""

from io import StringIO

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE3, TAGSTART_RE

from moin.converters.docbook_out import Converter
from moin.log import getLogger
from moin.utils.tree import html, moin_page, xlink, xml, docbook

logger = getLogger(__name__)

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
        logger.debug(f"After the docbook_OUT conversion : {string_to_parse}")
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
            '<page><body><p xml:base="http://base.tld" xml:id="myid" xml:lang="en">emphasised  <emphasis>text</emphasis></p></body></page>',
            # <article><simpara xml:base="http://base.tld" xml:id="myid" xml:lang="en">emphasised  <emphasis>text</emphasis></simpara></article>
            '/article/simpara[@xml:base="http://base.tld"][@xml:id="myid"][@xml:lang="en"]/emphasis[text()="text"]',
        ),
        # "Formal" paragraph with title
        (
            '<page><body><div html:class="db-formalpara" xml:id="myid"><div html:class="db-title">Heading</div><p>Text</p></div></body></page>',
            # <article><formalpara xml:id="myid"><title>Heading</title><simpara>Text</simpara></formalpara></article>
            '/article/formalpara[@xml:id="myid"][./title[text()="Heading"]]/simpara[text()="Text"]',
        ),
        # Paragraph with block-level child
        (
            '<page><body><div html:class="db-article"><div html:class="db-para">pre text <div html:class="db-example"><p>example</p></div> post text</div></div></body></page>',
            # <article><para>pre text <informalexample><para>example</para></informalexample> post text</para></article>
            "/article/para",
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
            '<page><body><table xml:id="myid"><table-body><table-row><table-cell page:number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
            # <article><table xml:id="myid"><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></article>
            '/article/table[@xml:id="myid"]/tbody/tr/td[@colspan="2"][text()="Cell"]',
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
        # Inline elements:
        (  # footnotes
            '<page><body><p>simple text<note page:note-class="footnote" xml:id="myid"><p>footnote content</p></note></p></body></page>',
            # <article><simpara>simple text<footnote xml:id="myid">footnote content</footnote></simpara></article>
            '/article/simpara[text()="simple text"]/footnote[@xml:id="myid"][simpara="footnote content"]',
        ),
        (  # additional reference to a footnote with ID
            '<page><body><p>additonal footnote reference<noteref xlink:href="#fn42" /></p></body></page>',
            # <article><simpara>additonal footnote reference<footnoteref linkend="fn42" /></simpara></article>
            '/article/simpara[text()="additonal footnote reference"]/footnoteref[@linkend="fn42"]',
        ),
        # Link conversion
        (
            '<page><body><p><a xlink:href="uri:test" xlink:title="title">link</a></p></body></page>',
            # <article><simpara><link xlink:href="uri:test" xlink:title="title">link</link></simpara></article>
            '/article/simpara/link[@xlink:href="uri:test"][@xlink:title="title"][text()="link"]',
        ),
        # CODE --> CODE
        (
            "<page><body><p><code>Text</code></p></body></page>",
            # <article><simpara><code>Text</code></simpara></article>
            '/article/simpara[code="Text"]',
        ),
        # KBD --> USERINPUT
        (
            "<page><body><p><kbd>Ctrl-X</kbd></p></body></page>",
            # <article><simpara><userinput>Ctrl-X</userinput></simpara></article>
            '/article/simpara[userinput="Ctrl-X"]',
        ),
        # LITERAL --> LITERAL
        (
            "<page><body><p><literal>monospaced</literal></p></body></page>",
            # <article><simpara><literal>monospaced</literal></simpara></article>
            '/article/simpara[literal="monospaced"]',
        ),
        # SAMP --> COMPUTEROUTPUT
        (
            "<page><body><p><samp>Error 42</samp></p></body></page>",
            # <article><simpara><computeroutput>Error 42</computeroutput></simpara></article>
            '/article/simpara[computeroutput="Error 42"]',
        ),
        # SPAN --> PHRASE
        (
            "<page><body><p><span>Text</span></p></body></page>",
            # <article><simpara><phrase>Text</phrase></simpara></article>
            '/article/simpara[phrase="Text"]',
        ),
        # SUB --> SUBSCRIPT
        (
            "<page><body><p><sub>sub</sub>script</p></body></page>",
            # <article><simpara><subscript>sub</subscript>script</simpara></article>
            '/article/simpara[text()="script"][subscript="sub"]',
        ),
        # SUP --> SUPERSCRIPT
        (
            "<page><body><p><sup>super</sup>script</p></body></page>",
            # <article><simpara></simpara><superscript>super</superscript>script</article>
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
        # restore original DocBook tag from ``html:class`` attribute:
        (  # <span html:class="db-shortcut"> --> <shortcut>
            '<page><body><p>press<span html:class="db-shortcut">Alt-X</span></p></body></page>',
            # <article><simpara>press<shortcut>Alt-X</shortcut></simpara></article>
            '/article/simpara/shortcut[text()="Alt-X"]',
        ),
        # restore original DocBook tag from ``page:html-tag`` attribute:
        (  # <emphasis page:html-tag="cite"> --> <citetitle>
            '<page><body><p>a <emphasis page:html-tag="cite">Title of Cited Work</emphasis></p></body></page>',
            # <article><simpara>a <citetitle>Title of Cited Work</citetitle></simpara></article>
            '/article/simpara/citetitle[text()="Title of Cited Work"]',
        ),
        (  # <emphasis page:html-tag="dfn"> --> <firstterm>
            '<page><body><p>A <emphasis page:html-tag="dfn">mopple</emphasis> is …</p></body></page>',
            # <article><simpara>A <firstterm>mopple</firstterm> is …</simpara></article>
            '/article/simpara/firstterm[text()="mopple"]',
        ),
        (  # <emphasis page:html-tag="i"> --> <foreignphrase>
            '<page><body><p>They reached a <emphasis page:html-tag="i">cul de sac</emphasis>.</p></body></page>',
            # <article><simpara>They reached a <foreignphrase>cul de sac</foreignphrase>.</simpara></article>
            '/article/simpara/foreignphrase[text()="cul de sac"]',
        ),
        (  # <emphasis page:html-tag="var"> --> <varname>
            '<page><body><p><emphasis page:html-tag="var">x</emphasis> = 3</p></body></page>',
            # <article><simpara><varname>x</varname> = 3</simpara></article>
            '/article/simpara/varname[text()="x"]',
        ),
        (  # <span page:html-tag="abbr"> --> <abbrev>
            '<page><body><p><span page:html-tag="abbr">DOM</span> stands for …</p></body></page>',
            # <article><simpara><abbrev>DOM</abbrev> stands for …</simpara></article>
            '/article/simpara/abbrev[text()="DOM"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_inline_elements(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Block elements
        (  # <blockcode> --> <screen> with CDATA
            "<page><body><blockcode>Text</blockcode></body></page>",
            # <article><screen><![CDATA[Text]]></screen></article>
            '/article[screen="<![CDATA[Text]]>"]',
        ),
        (  # BLOCKQUOTE --> BLOCKQUOTE
            '<page><body><blockquote page:source="Socrates" xml:id="myid">One thing only I know, and that is that I know nothing.</blockquote></body></page>',
            # <article><blockquote xml:id="myid"><attribution>Socrates</attribution><simpara>One thing ... nothing</simpara></blockquote></article>
            '/article/blockquote[@xml:id="myid"][attribution="Socrates"][simpara="One thing only I know, and that is that I know nothing."]',
        ),
        # restore original DocBook tag from ``html:class`` attribute:
        (  # <div html:class="db-epigraph"> --> <epigraph>
            '<page><body><div html:class="db-epigraph"><p>to my wife</p></div></body></page>',
            # <article><epigraph><simpara>to my wife</simpara></epigraph></article>
            '/article/epigraph/simpara[text()="to my wife"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_block_elements(self, input, xpath):
        self.do(input, xpath)

    data = [
        # media objects
        (
            '<page><body><p><object xlink:href="pics.png" page:type="image/" /></p></body></page>',
            # <article><simpara><inlinemediaobject><imageobject><imagedata fileref="pics.png"></imageobject></inlinemediaobject></simpara></article>
            '/article/simpara/inlinemediaobject/imageobject/imagedata[@fileref="pics.png"]',
        ),
        (
            '<page><body><p><object xlink:href="sound.wav" page:type="audio/" xml:lang="fr" /></p></body></page>',
            # <article><simpara><inlinemediaobject xml:lang="fr"><audioobject><audiodata fileref="sound.wav"></audioobject></inlinemediaobject></simpara></article>
            '/article/simpara/inlinemediaobject[@xml:lang="fr"]/audioobject/audiodata[@fileref="sound.wav"]',
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
