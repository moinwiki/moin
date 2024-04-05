# Copyright: 2010 MoinMoin:ValentinJaniaut
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.docbook_in
"""

from io import StringIO

import pytest

from . import serialize, XMLNS_RE3, TAGSTART_RE

from moin.utils.tree import html, moin_page, xlink, xml, docbook, xinclude
from moin.converters.docbook_in import Converter

from moin import log

logging = log.getLogger(__name__)

etree = pytest.importorskip("lxml.etree")  # noqa


class Base:
    input_namespaces = ns_all = f'xmlns="{docbook.namespace}" xmlns:xlink="{xlink.namespace}"'
    output_namespaces = {
        moin_page.namespace: "",
        xlink.namespace: "xlink",
        xml.namespace: "xml",
        html.namespace: "html",
        xinclude.namespace: "xinclude",
    }

    namespaces_xpath = {
        "xlink": xlink.namespace,
        "xml": xml.namespace,
        "html": html.namespace,
        "xinclude": xinclude.namespace,
    }

    input_re = TAGSTART_RE
    output_re = XMLNS_RE3

    def handle_input(self, input):
        return self.input_re.sub(r"\1 " + self.input_namespaces, input)

    def handle_output(self, input, **args):
        if "nonamespace" not in args:
            to_conv = self.handle_input(input)
        elif args["nonamespace"]:
            to_conv = input
        out = self.conv(to_conv, "application/docbook+xml;charset=utf-8")
        output = serialize(out, namespaces=self.output_namespaces)
        return self.output_re.sub("", output)

    def do(self, input, xpath_query):
        string_to_parse = self.handle_output(input)
        logging.debug(f"After the DOCBOOK_IN conversion : {string_to_parse}")
        tree = etree.parse(StringIO(string_to_parse))
        print("string_to_parse = %s" % string_to_parse)  # provide a clue for failing tests
        assert tree.xpath(xpath_query, namespaces=self.namespaces_xpath)

    def do_nonamespace(self, input, xpath_query):
        string_to_parse = self.handle_output(input, nonamespace=True)
        logging.debug(f"After the DOCBOOK_IN conversion : {string_to_parse}")
        tree = etree.parse(StringIO(string_to_parse))
        assert tree.xpath(xpath_query, namespaces=self.namespaces_xpath)


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        (
            "<article><para>Test</para></article>",
            # <page><body><div html:class="db-article"><p>Test</p></div></body></page>
            '/page/body/div[@html:class="db-article"][p="Test"]',
        ),
        (
            "<article><simpara>Test</simpara></article>",
            # <page><body><div html:class="article"><p>Test</p></div></body></page>
            '/page/body/div[p="Test"]',
        ),
        (
            "<article><formalpara><title>Title</title><para>Test</para></formalpara></article>",
            # <page><body><div html:class="article"><p html:title="Title">Test</p></div></body></page>
            '/page/body/div/p[text()="Test"][@html:title="Title"]',
        ),
        (
            "<article><sect1><title>Heading 1</title> <para>First Paragraph</para></sect1></article>",
            # <page><body><div html:class="article"><h outline-level="1">Heading 1</h><p>First Paragraph</p></div></body></page>
            '/page/body/div[./h[@outline-level="1"][text()="Heading 1"]][./p[text()="First Paragraph"]]',
        ),
        # Test for conversion with unicode char
        (
            "<article><para>안녕 유빈</para></article>",
            # <page><body><div html:class="article"><p>안녕 유빈</p></div></body></page>
            '/page/body/div[p="안녕 유빈"]',
        ),
        # Ignored tags
        (
            "<article><info><title>Title</title><author>Author</author></info><para>text</para></article>",
            # <page><body><div html:class="article"><p>text</p></div></body></page>
            '/page/body/div[p="text"]',
        ),
        # XML attributes: We support all the xml standard attributes
        (
            '<article><para xml:base="http://base.tld" xml:id="id" xml:lang="en">Text</para></article>',
            # <page><body><div html:class="article"><p xml:base="http://base.tld" xml:id="id" xml:lang="en">Text</p></div></body></page>
            '/page/body/div/p[@xml:base="http://base.tld"][@xml:id="id"][@xml:lang="en"][text()="Text"]',
        ),
        # ANCHOR --> SPAN
        (
            '<article><para>bla bla<anchor xml:id="point_1" />bla bla</para></article>',
            # <page><body><div html:class="article"><p>bla bla<span class="db-anchor" xml:id="point_1" />bla bla</p></div></body></page>
            '/page/body/div/p/span[@html:class="db-anchor"][@xml:id="point_1"]',
        ),
        # BOOK Document
        (
            "<book><para>Test</para></book>",
            # <page><body><div html:class="db-book"><p>Test</p></div></body></page>
            '/page/body/div[@html:class="db-book"][p="Test"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_base(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Test simple numbered section conversion into headings.
        (
            "<article><sect1><title>Heading 1</title> <para>First</para><sect2><title>Heading 2</title><para>Second</para></sect2></sect1></article>",
            # <page><body><table-of-content><div html:class="article"><h outline-level="1">Heading 1</h><p>First</p><h outline-level="2">Heading 2</h><p>Second</p></div></body></page>
            '/page/body[table-of-content]/div[h[1][@outline-level="1"][text()="Heading 1"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2"]][p[2][text()="Second"]]',
        ),
        (
            "<article><section><title>Heading 1</title> <para>First</para><section><title>Heading 2</title><para>Second</para></section></section></article>",
            # <page><body><table-of-content><div html:class="article"><h outline-level="1">Heading 1</h><p>First</p><h outline-level="2">Heading 2</h><p>Second</p></div></body></page>
            '/page/body[table-of-content]/div[h[1][@outline-level="1"][text()="Heading 1"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2"]][p[2][text()="Second"]]',
        ),
        # Test complex recursive section conversion into headings.
        (
            "<article><section><title>Heading 1 A</title><para>First</para><section><title>Heading 2 A</title><para>Second</para><section><title>Heading 3 A</title><para>Third</para></section></section></section><section><title>Heading 1 B</title><para>Fourth</para></section></article>",
            # <page><body><table-of-content /><div html:class="article"><h outline-level="1">Heading 1 A</h><p>First</p><h outline-level="2">Heading 2 A</h><p>Second</p><h outline-level="3">Heading 3 A</h><p>Third</p><h outline-level="1">Heading 1 B</h><p>Fourth</p></div></body></page>
            '/page/body[table-of-content]/div[h[1][@outline-level="1"][text()="Heading 1 A"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2 A"]][p[2][text()="Second"]][h[3][@outline-level="3"][text()="Heading 3 A"]][p[3][text()="Third"]][h[4][@outline-level="1"][text()="Heading 1 B"]][p[4][text()="Fourth"]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_title(self, input, xpath):
        self.do(input, xpath)

    data = [
        # ITEMIZED LIST --> unordered list
        (
            "<article><itemizedlist><listitem>Unordered Item 1</listitem><listitem>Unordered Item 2</listitem></itemizedlist></article>",
            # <page><body><div html:class="article"><list item-label-generate="unordered"><list-item><list-item-body>Unordered Item 1</list-item-body></list-item><list-item><list-item-body>Unordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Unordered Item 1"]][list-item[2]/list-item-body[text()="Unordered Item 2"]]',
        ),
        # ORDERED LIST --> ordered list
        (
            "<article><orderedlist><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>",
            # <page><body><div html:class="article"><list item-label-generate="ordered"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]',
        ),
        # ORDERED LIST with upperalpha numeration --> ordered list with upper-alpha list-style-type
        (
            '<article><orderedlist numeration="upperalpha"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
            # <page><body><div html:class="article"><list item-label-generage="ordered" list-style-type="upper-alpha"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][@list-style-type="upper-alpha"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]',
        ),
        # ORDERED LIST with loweralpha numeration --> ordered list with lower-alpha list-style-type
        (
            '<article><orderedlist numeration="loweralpha"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
            # <page><body><div html:class="article"><list item-label-generage="ordered" list-style-type="lower-alpha"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][@list-style-type="lower-alpha"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]',
        ),
        # ORDERED LIST with upperroman numeration --> ordered list with upper-roman list-style-type
        (
            '<article><orderedlist numeration="upperroman"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
            # <page><body><div html:class="article"><list item-label-generage="ordered" list-style-type="upper-roman"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][@list-style-type="upper-roman"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]',
        ),
        # ORDERED LIST with lowerroman numeration --> ordered list with lower-roman list-style-type
        (
            '<article><orderedlist numeration="lowerroman"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
            # <page><body><div html:class="article"><list item-label-generage="ordered" list-style-type="lower-roman"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][@list-style-type="lower-roman"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]',
        ),
        # VARIABLE LIST --> list
        (
            "<article><variablelist><varlistentry><term>Term 1</term><listitem>Definition 1</listitem></varlistentry><varlistentry><term>Term 2</term><listitem>Definition 2</listitem></varlistentry></variablelist></article>",
            # <page><body><div html:class="article"><list><list-item><list-item-label>Termm 1</list-item-label><list-item-body>Definition 1</list-item-body></list-item><list-item><list-item-label>Term 2</list-item-label><list-item-body>Definition 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[list-item[1][list-item-label="Term 1"][list-item-body="Definition 1"]][list-item[2][list-item-label="Term 2"][list-item-body="Definition 2"]]',
        ),
        # PROCEDURE --> ordered list (with arabic numeration)
        (
            "<article><procedure><step>First Step</step><step>Second Step</step></procedure></article>",
            # <page><body><div html:class="article"><list item-label-generate="ordered"><list-item><list-item-body>First Step</list-item-body></list-item><list-item><list-item-body>Second Step</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="First Step"]][list-item[2]/list-item-body[text()="Second Step"]]',
        ),
        # PROCEDURE --> ordered list (with arabic numeration) (with stepalternative)
        (
            "<article><procedure><step>First Step</step><stepalternatives>Second Step</stepalternatives></procedure></article>",
            # <page><body><div html:class="article"><list item-label-generate="ordered"><list-item><list-item-body>First Step</list-item-body></list-item><list-item><list-item-body>Second Step</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="First Step"]][list-item[2]/list-item-body[text()="Second Step"]]',
        ),
        # PROCEDURE with SUBSTEPS
        (
            "<article><procedure><step>First Step</step><substeps><step>Second Step</step></substeps></procedure></article>",
            # <page><body><div html:class="article"><list item-label-generate="ordered"><list-item><list-item-body>First Step</list-item-body></list-item><list-item><list-item-body><list item-label-generate="ordered">Second Step</list-item-body></list-item></list></list></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="First Step"]][list[@item-label-generate="ordered"]/list-item/list-item-body[text()="Second Step"]]',
        ),
        # GLOSS LIST --> Definition list
        (
            "<article><glosslist><glossentry><glossterm>Term 1</glossterm><glossdef><para>Definition 1</para></glossdef></glossentry><glossentry><glossterm>Term 2</glossterm><glossdef><para>Definition 2</para></glossdef></glossentry></glosslist></article>",
            # <page><body><div html:class="article"><list><list-item><list-item-label>Termm 1</list-item-label><list-item-body>Definition 1</list-item-body></list-item><list-item><list-item-label>Term 2</list-item-label><list-item-body>Definition 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[list-item[1][list-item-label="Term 1"][list-item-body[p="Definition 1"]]][list-item[2][list-item-label="Term 2"][list-item-body[p="Definition 2"]]]',
        ),
        # SEGMENTED LIST --> Definition List
        (
            "<article><segmentedlist><segtitle>Term 1</segtitle><segtitle>Term 2</segtitle><segtitle>Term 3</segtitle><seglistitem><seg>Def 1:1</seg><seg>Def 1:2</seg><seg>Def 1:3</seg></seglistitem><seglistitem><seg>Def 2:1</seg><seg>Def 2:2</seg><seg>Def 2:3</seg></seglistitem></segmentedlist></article>",
            '/page/body/div/list[list-item[1][list-item-label="Term 1"][list-item-body="Def 1:1"]][list-item[2][list-item-label="Term 2"][list-item-body="Def 1:2"]][list-item[3][list-item-label="Term 3"][list-item-body="Def 1:3"]][list-item[4][list-item-label="Term 1"][list-item-body="Def 2:1"]][list-item[5][list-item-label="Term 2"][list-item-body="Def 2:2"]][list-item[6][list-item-label="Term 3"][list-item-body="Def 2:3"]]',
        ),
        # SIMPLE LIST --> unordered list
        (
            "<article><simplelist><member>Item 1</member><member>Item 2</member></simplelist></article>",
            # <page><body><div html:class="article"><list item-label-generate="unordered"><list-item><list-item-body>Unordered Item 1</list-item-body></list-item><list-item><list-item-body>Unordered Item 2</list-item-body></list-item></list></div></body></page>
            '/page/body/div/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Item 1"]][list-item[2]/list-item-body[text()="Item 2"]]',
        ),
        # Q and A set with defaultlabel = number --> ordered list
        (
            "<article><qandaset defaultlabel='number'><qandaentry><question><para>Question 1</para></question><answer><para>Answer 1</para></answer></qandaentry><qandaentry><question><para>Question 2</para></question><answer><para>Answer 2</para></answer></qandaentry></qandaset></article> ",
            # <page><body><div html:class="article"><list item-label-generate="ordered"><list-item><list-item-body><p>Question1</p><p>Answer 1</p></list-item-body></list-item><list-item><list-item-body><p>Question 2</p><p>Answer 2</p></list-item-body></list-item></div></body></page>
            '/page/body/div/list[@item-label-generate="ordered"][list-item[1]/list-item-body[p[1][text()="Question 1"]][p[2][text()="Answer 1"]]][list-item[2]/list-item-body[p[1][text()="Question 2"]][p[2][text()="Answer 2"]]]',
        ),
        # Q and A set with defaultlabel = qanda --> definition list, with Q: and A: for the label
        (
            "<article><qandaset defaultlabel='qanda'><qandaentry><question><para>Question 1</para></question><answer><para>Answer 1</para></answer></qandaentry><qandaentry><question><para>Question 2</para></question><answer><para>Answer 2</para></answer></qandaentry></qandaset></article> ",
            # <page><body><div html:class="article"><list><list-item><list-item-label>Q: </list-item-label><list-item-body>Question 1</list-item-body></list-item><list-item><list-item-label>A: </list-item-label><list-item-body>Answer 1</list-item-body></list-item><list-item><list-item-label>Q: </list-item-label><list-item-body>Question 2</list-item-body></list-item><list-item><list-item-label>A: </list-item-label><list-item-body>Answer 2</list-item-body></list-item>
            '/page/body/div/list[list-item[1][list-item-label="Q:"][list-item-body="Question 1"]][list-item[2][list-item-label="A:"][list-item-body="Answer 1"]][list-item[3][list-item-label="Q:"][list-item-body="Question 2"]][list-item[4][list-item-label="A:"][list-item-body="Answer 2"]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_list(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<article><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></article>",
            # <page><body><div html:class="article"><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-row></table-cell></table></div></body></page>
            '/page/body/div/table[./table-header/table-row[table-cell="Header"]][./table-footer/table-row[table-cell="Footer"]][./table-body/table-row[table-cell="Cell"]]',
        ),
        (
            '<article><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></article>',
            # <page><body><div html:class="article"><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></div></body></page>
            '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-columns-spanned="2"]',
        ),
        (
            '<article><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></article>',
            # <page><body><div html:class="article"><table><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></div></body></page>
            '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-rows-spanned="2"]',
        ),
        # Simple db.cals.table
        (
            '<article><table xml:id="ex.calstable"><tgroup cols="2"><thead><row><entry>a1</entry><entry>a2</entry></row></thead><tfoot><row><entry>f1</entry><entry>f2</entry></row></tfoot><tbody><row><entry>b1</entry><entry>b2</entry></row></tbody></tgroup></table></article>',
            # <page><body><div html:class="article"><table><table-header><table-row><table-cell>a1</table-cell><table-cell>a2</table-cell></table-row></table-header><table-footer><table-row><table-cell>f1</table-cell><table-cell>f2</table-cell></table-row></table-footer><table-body><table-row><table-cell>b1</table-row><table-cell>b2</table-row></table-cell></table></div></body></page>
            '/page/body/div/table[./table-header/table-row[table-cell="a1"][table-cell="a2"]][./table-footer/table-row[table-cell="f1"][table-cell="f2"]][./table-body/table-row[table-cell="b1"][table-cell="b2"]]',
        ),
        # db.cals.table with entry table.
        (
            '<article><table xml:id="ex.calstable"><tgroup cols="1"><thead><row><entry>a1</entry></row></thead><tfoot><row><entry>f1</entry></row></tfoot><tbody><row><entrytbl cols="1"><tbody><row><entry>s1</entry></row></tbody></entrytbl></row></tbody></tgroup></table></article>',
            # <page><body><div html:class="article"><table><table-header><table-row><table-cell>a1</table-cell></table-row></table-header><table-footer><table-row><table-cell>f1</table-cell></table-row></table-footer><table-body><table-row><table-cell><table><table-body><table-row><table-cell>s1</table-cell></table-row></table-body></table></table-row></table-cell></table></div></body></page>
            '/page/body/div/table[./table-header/table-row[table-cell="a1"]][./table-footer/table-row[table-cell="f1"]][./table-body/table-row[table-cell/table/table-body/table-row[table-cell="s1"]]]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_table(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<article><para>Text Para<footnote><para>Text Footnote</para></footnote></para></article>",
            # <page><body><div html:class="article"><p>Text Para<note note-class="footnote"><note-body><p>Text Footnote</p></note-body></note></p></div></body></page>
            '/page/body/div/p[text()="Text Para"]/note[@note-class="footnote"]/note-body/p[text()="Text Footnote"]',
        ),
        (
            "<article><para><quote>text</quote></para></article>",
            # <page><body><div html:class="article"><p><quote>text</quote></para></article>
            '/page/body/div/p[quote="text"]',
        ),
        # Test span for inline element
        (
            "<article><para><abbrev>ABBREV</abbrev></para></article>",
            # <page><body><div html:class="article"><p><span class="db-abbrev">ABBREV</span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-abbrev"][text()="ABBREV"]',
        ),
        # Test div for block element
        (
            "<article><acknowledgements><para>Text</para></acknowledgements></article>",
            # <page><body><div html:class="article"><div html:class="db-acknowledgements"><p>Text</p></div></div></body></page>
            '/page/body/div/div[@html:class="db-acknowledgements"][p="Text"]',
        ),
        # Test for <informalequation>
        (
            "<article><informalequation><para>E = mc^2</para></informalequation></article>",
            # <page><body><div html:class="article"><div html:class="db-equation"><p>E = mc^2</p></div></div></body></page>
            '/page/body/div/div[@html:class="db-equation"][p="E = mc^2"]',
        ),
        # Test for <informalexample>
        (
            "<article><informalexample><para>example</para></informalexample></article>",
            # <page><body><div html:class="article"><div html:class="db-example"><p>example</p></div></div></body></page>
            '/page/body/div/div[@html:class="db-example"][p="example"]',
        ),
        # Test for <sbr />
        (
            "<article><cmdsynopsis><para>Line 1<sbr />Line 2</para></cmdsynopsis></article>",
            # <page><body><div html:class="article"><div html:class="db-cmdsynopsis"><p>Line 1<line-break />Line 2</p></div></div></body></page>
            '/page/body/div/div[@html:class="db-cmdsynopsis"]/p/line-break',
        ),
        # Test for <tag> element with class and namespace attribute
        (
            '<article><para><tag class="attribute" namespace="namespace">TAG</tag></para></article>',
            # <page><body><div html:class="article"><p><span class="db-tag-attribute">{namespace}TAG</span></p></div></article>
            '/page/body/div/p/span[@html:class="db-tag-attribute"][text()="{namespace}TAG"]',
        ),
        # Test for <tag> element without class and namespace attribute
        (
            "<article><para><tag>TAG</tag></para></article>",
            # <page><body><div html:class="article"><p><span class="db-tag">TAG</span></p></div></article>
            '/page/body/div/p/span[@html:class="db-tag"][text()="TAG"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_misc(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Normal link, with conversion of all the xlink attributes
        (
            '<article><para><link xlink:href="http:test" xlink:title="title">link</link></para></article>',
            # <page><body><div html:class="article"><p><a xlink:href="http:test" xlink:title="title">link</a></p></div></body></page>
            '/page/body/div/p/a[@xlink:href="http:test"][@html:title="title"][text()="link"]',
        ),
        # Old link from DocBook v.4.X for backward compatibility
        (
            '<article><para><ulink url="http:test">link</ulink></para></article>',
            # <page><body><div html:class="article"><p><a xlink:href="http:test">link</a></p></div></body></page>
            '/page/body/div/p/a[@xlink:href="http:test"][text()="link"]',
        ),
        # Normal link, with linkend attribute
        (
            '<article><para><link linkend="anchor">link</link></para></article>',
            # <page><body><div html:class="article"><p><a xlink:href="#anchor">link</a></p></div></body></page>
            '/page/body/div/p/a[@xlink:href="wiki.local:#anchor"][text()="link"]',
        ),
        # OLINK
        (
            '<article><para><olink targetdoc="uri" targetptr="anchor">link</olink></para></article>',
            # <page><body><div html:class="article"><para><a xlink:href="uri#anchor">link</a></para></div></body></page>
            '/page/body/div/p/a[@xlink:href="uri#anchor"][text()="link"]',
        ),
        # Link w/ javascript: scheme
        (
            "<article><para><ulink url=\"javascript:alert('xss')\">link</ulink></para></article>",
            # the href attribute will default to None because javascript is not an allowed url scheme
            # we don't care how it gets rendered as long as the javascript doesn't show up
            # <page><body><div html:class="article"><p><a xlink:href="None">link</a></p></div></body></page>
            '/page/body/div/p/a[@xlink:href="None"][text()="link"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_link(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            "<article><screen>Text</screen></article>",
            # <page><body><div html:class="article"><blockcode>Text</blockcode></div></body></page>
            '/page/body/div[blockcode="Text"]',
        ),
        # Test for <screen> with CDATA
        (
            "<article><screen><![CDATA[Text]]></screen></article>",
            # <page><body><div html:class="article"><blockcode>Text</blockcode></div></body></page>
            '/page/body/div[blockcode="Text"]',
        ),
        # PROGRAMLISTING --> BLOCKCODE
        (
            "<article><programlisting>Text</programlisting></article>",
            # <page><body><div html:class="article"><blockcode>Text</blockcode></div></body></page>
            '/page/body/div[blockcode="Text"]',
        ),
        # LITERAL --> CODE
        (
            "<article><para>text<literal>literal</literal></para></article>",
            # <page><body><div html:class="article"><p>text<code>literal</code></p></div></body></page>
            '/page/body/div/p[text()="text"][code="literal"]',
        ),
        (
            "<article><blockquote><attribution>author</attribution>text</blockquote></article>",
            # <page><body><div html:class="article"><blockquote source="author">text</blockquote></div></body></page>
            '/page/body/div/blockquote[@source="author"][text()="text"]',
        ),
        # CODE --> CODE
        (
            "<article><para><code>Text</code></para></article>",
            # <page><body><div html:class="article"><p><code>Text</code></p></article>
            '/page/body/div/p[code="Text"]',
        ),
        # COMPUTEROUTPUT --> CODE
        (
            "<article><para><computeroutput>Text</computeroutput></para></article>",
            # <page><body><div html:class="article"><p><code>Text</code></p></article>
            '/page/body/div/p[code="Text"]',
        ),
        # MARKUP --> CODE
        (
            "<article><para><markup>Text</markup></para></article>",
            # <page><body><div html:class="article"><p><code>Text</code></p></article>
            '/page/body/div/p[code="Text"]',
        ),
        # LITERALLAYOUT --> BLOCKCODE
        (
            "<article><literallayout>Text</literallayout></article>",
            # <page><body><div html:class="article"><blockcode html:class="db-literallayout">Text</blockcode></div></body></page>
            '/page/body/div/blockcode[text()="Text"][@html:class="db-literallayout"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_code(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Test for image object
        (
            '<article><para><inlinemediaobject><imageobject><imagedata fileref="test.png"/></imageobject></inlinemediaobject></para></article>',
            # <page><body><div html:class="db-article"><p><xinclude:include html:alt="test.png" xinclude:href="wiki.local:test.png" /></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-inlinemediaobject"]/xinclude:include[@html:alt="test.png"][@xinclude:href="wiki.local:test.png"]',
        ),
        # Test for audio object
        (
            '<article><para><inlinemediaobject><audioobject><audiodata fileref="test.wav"/></audioobject></inlinemediaobject></para></article>',
            # <page><body><div html:class="db-article"><p><span html:class="db-inlinemediaobject"><xinclude:include type="audio/" html:alt="test.wav" xinclude:href="wiki.local:test.wav" /></span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-inlinemediaobject"]/xinclude:include[@xinclude:href="wiki.local:test.wav"][@type="audio/"]',
        ),
        # Test for video object
        (
            '<article><para><mediaobject><videoobject><videodata fileref="test.avi"/></videoobject></mediaobject></para></article>',
            # <page><body><div html:class="db-article"><p><div html:class="db-mediaobject"><xinclude:include type="video/" html:alt="test.avi" xinclude:href="wiki.local:test.avi" /></div></p></div></body></page>
            '/page/body/div/p/div[@html:class="db-mediaobject"]/xinclude:include[@xinclude:href="wiki.local:test.avi"][@type="video/"]',
        ),
        # Test for image object with different imagedata
        (
            '<article><mediaobject><imageobject><imagedata fileref="figures/eiffeltower.eps" format="EPS"/></imageobject><imageobject><imagedata fileref="figures/eiffeltower.png" format="PNG"/></imageobject><textobject><phrase>The Eiffel Tower</phrase> </textobject><caption><para>Designed by Gustave Eiffel in 1889, The Eiffel Tower is one of the most widely recognized buildings in the world.</para>  </caption></mediaobject></article>',
            # <page><body><div html:class="db-article"><div html:class="db-mediaobject"><span><xinclude:include type="image/png" html:alt="figures/eiffeltower.png" xinclude:href="wiki.local:figures/eiffeltower.png" /><span class="db-caption"><p>Designed by Gustave Eiffel in 1889, The Eiffel Tower is one of the most widely recognized buildings in the world.</p></span></span></div></div></body></page>
            '/page/body/div/div[@html:class="db-mediaobject"]/span/xinclude:include[@xinclude:href="wiki.local:figures/eiffeltower.png"][@type="image/png"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_object(self, input, xpath):
        self.do(input, xpath)

    data = [
        # EMPHASIS --> EMPHASIS
        (
            "<article><para>text<emphasis>emphasis</emphasis></para></article>",
            # <page><body><div html:class="article"><p>text<emphasis>emphasis</emphasis></p></div></body></page>
            '/page/body/div/p[text()="text"][emphasis="emphasis"]',
        ),
        # EMPHASIS role='strong' --> STRONG
        (
            '<article><para>text<emphasis role="strong">strong</emphasis></para></article>',
            # <page><body><div html:class="db-article"><p>text<emphasis>strong</emphasis></p></div></body></page>
            '/page/body/div/p[text()="text"]/emphasis[text()="strong"]',
        ),
        # SUBSCRIPT --> SPAN baseline-shift = 'sub'
        (
            "<article><para><subscript>sub</subscript>script</para></article>",
            # <page><body><div html:class="article"><p>script<span baseline-shift="sub">sub</span></p></div></body></page>
            '/page/body/div/p[text()="script"]/span[@baseline-shift="sub"][text()="sub"]',
        ),
        # SUPERSCRIPT --> SPAN baseline-shift = 'super'
        (
            "<article><para><superscript>super</superscript>script</para></article>",
            # <page><body><div html:class="article"><p>script<span baseline-shift="super">super</span></p></div></body></page>
            '/page/body/div/p[text()="script"]/span[@baseline-shift="super"][text()="super"]',
        ),
        # PHRASE --> SPAN
        (
            "<article><para><phrase>text</phrase></para></article>",
            # <page><body><div html:class="article"><p><span>text</span></p></div></body></page>
            '/page/body/div/p[span="text"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_style_element(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Test for caution admonition
        (
            "<article><caution><para>text</para></caution></article>",
            # <page><body><div html:class="article"><admonition type='caution'><p>text<p></admonition></div></body></page>
            '/page/body/div/admonition[@type="caution"][p="text"]',
        ),
        # Test for important admonition
        (
            "<article><important><para>text</para></important></article>",
            # <page><body><div html:class="article"><admonition type='important'><p>text<p></admonition></div></body></page>
            '/page/body/div/admonition[@type="important"][p="text"]',
        ),
        # Test for note admonition
        (
            "<article><note><para>text</para></note></article>",
            # <page><body><div html:class="article"><admonition type='note'><p>text<p></admonition></div></body></page>
            '/page/body/div/admonition[@type="note"][p="text"]',
        ),
        # Test for tip admonition
        (
            "<article><tip><para>text</para></tip></article>",
            # <page><body><div html:class="article"><admonition type='tip'><p>text<p></admonition></div></body></page>
            '/page/body/div/admonition[@type="tip"][p="text"]',
        ),
        # Test for warning admonition
        (
            "<article><warning><para>text</para></warning></article>",
            # <page><body><div html:class="article"><admonition type='warning'><p>text<p></admonition></div></body></page>
            '/page/body/div/admonition[@type="warning"][p="text"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_admonition(self, input, xpath):
        self.do(input, xpath)

    data = [
        (
            '<article><para><trademark class="copyright">MoinMoin</trademark></para></article>',
            # <page><body><div html:class="db-article"><p><span html:class="db-trademark">\xa9  MoinMoin</span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-trademark"][text()="\xa9 MoinMoin"]',
        ),
        (
            '<article><para><trademark class="registered">Nutshell Handbook</trademark></para></article>',
            # <page><body><div html:class="db-article"><p><span html:class="db-trademark">Nutshell Handbook\xae</span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-trademark"][text()="Nutshell Handbook\xae"]',
        ),
        (
            '<article><para><trademark class="trade">Foo Bar</trademark></para></article>',
            # <page><body><div html:class="db-article"><p><span html:class="db-trademark">Foo Bar\u2122</span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-trademark"][text()="Foo Bar\u2122"]',
        ),
        (
            '<article><para><trademark class="service">MoinMoin</trademark></para></article>',
            # <page><body><div html:class="article"><p><span class="db-trademark">MoinMoin<span baseline-shift="super">SM</span></span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-trademark"][text()="MoinMoin"]/span[@baseline-shift="super"][text()="SM"]',
        ),
        (
            "<article><para><trademark>MoinMoin</trademark></para></article>",
            # <page><body><div html:class="article"><p><span class="db-trademark">MoinMoin</span></p></div></body></page>
            '/page/body/div/p/span[@html:class="db-trademark"][text()="MoinMoin"]',
        ),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_trademark(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Error: Xml not correctly formatted
        ("<article><para>Text</para>", "/page/body/part/error"),
        # Error: Root Element is not correct
        ('<link xlink:href="uri">link</link>', "/page/body/part/error"),
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_error(self, input, xpath):
        self.do(input, xpath)

    data = [
        # Error: Missing namespace
        ("<article><para>Text</para></article>", "/page/body/part/error")
    ]

    @pytest.mark.parametrize("input,xpath", data)
    def test_namespace(self, input, xpath):
        self.do_nonamespace(input, xpath)
