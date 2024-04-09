# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.rst_in
"""

import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import html, moin_page, xlink, xinclude
from moin.converters.rst_in import Converter


class TestConverter:
    namespaces = {moin_page.namespace: "", xlink.namespace: "xlink", html: "xhtml", xinclude: "xinclude"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ("Text", "<page><body><p>Text</p></body></page>"),
        ("Text\nTest", "<page><body><p>Text\nTest</p></body></page>"),
        ("Text\n\nTest", "<page><body><p>Text</p><p>Test</p></body></page>"),
        (
            "H\\ :sub:`2`\\ O\n\nE = mc\\ :sup:`2`",
            '<page><body><p>H<span baseline-shift="sub">2</span>O</p><p>E = mc<span baseline-shift="super">2</span></p></body></page>',
        ),
        (
            "| Lend us a couple of bob till Thursday.",
            "<page><body><line-block><line-blk>Lend us a couple of bob till Thursday.</line-blk></line-block></body></page>",
        ),
        ("**Text**", "<page><body><p><strong>Text</strong></p></body></page>"),
        ("*Text*", "<page><body><p><emphasis>Text</emphasis></p></body></page>"),
        ("``Text``", "<page><body><p><code>Text</code></p></body></page>"),
        (
            "`Text <javascript:alert('xss')>`_",
            '<page><body><p><admonition type="error">Text</admonition></p></body></page>',
        ),
        (
            "Text\n\n~~~~~\n\nTest",
            '<page><body><p>Text</p><separator xhtml:class="moin-hr3" /><p>Test</p></body></page>',
        ),
        (".. comment", '<page><body><div class="comment dashed">comment</div></body></page>'),
        ("..\n comment", '<page><body><div class="comment dashed">comment</div></body></page>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            "1. a\n   b\n   c\n\n2. b\n\n   d",
            """<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>a
b
c</p></list-item-body></list-item><list-item><list-item-body><p>b</p><p>d</p></list-item-body></list-item></list></body></page>""",
        ),
        (
            "1. a\n2. b\n\nA. c\n\na. A\n\n   1. B\n\n   2. C\n\n",
            '<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>a</p></list-item-body></list-item><list-item><list-item-body><p>b</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body><p>c</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body><p>A</p><list item-label-generate="ordered"><list-item><list-item-body><p>B</p></list-item-body></list-item><list-item><list-item-body><p>C</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>',
        ),
        (
            "* A\n\n   - B\n\n      + C\n\n   - D\n\n* E",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body><p>A</p><blockquote><list item-label-generate="unordered"><list-item><list-item-body><p>B</p><blockquote><list item-label-generate="unordered"><list-item><list-item-body><p>C</p></list-item-body></list-item></list></blockquote></list-item-body></list-item><list-item><list-item-body><p>D</p></list-item-body></list-item></list></blockquote></list-item-body></list-item><list-item><list-item-body><p>E</p></list-item-body></list-item></list></body></page>',
        ),
        (
            "what\n      def\n\nhow\n      to",
            "<page><body><list><list-item><list-item-label>what</list-item-label><list-item-body><p>def</p></list-item-body></list-item><list-item><list-item-label>how</list-item-label><list-item-body><p>to</p></list-item-body></list-item></list></body></page>",
        ),
        # starting an ordered list with a value other than 1 generates an error
        (
            " 3. A\n #. B",
            '<page><body><blockquote><list item-label-generate="ordered"><list-item><list-item-body><p>A</p>'
            "</list-item-body></list-item><list-item><list-item-body><p>B</p></list-item-body></list-item></list>"
            '<admonition type="error"><p>Enumerated list start value not ordinal-1: "3" (ordinal 3)</p></admonition>'
            "</blockquote></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            "term 1\n definition 1",
            "<page><body><list><list-item><list-item-label>term 1</list-item-label><list-item-body><p>definition 1</p></list-item-body></list-item></list></body></page>",
        ),
        (
            "term 2 : classifier 1 : classifier 2\n definition 2",
            "<page><body><list><list-item><list-item-label>term 2<span>:classifier 1</span><span>:classifier 2</span></list-item-label>classifier 1classifier 2<list-item-body><p>definition 2</p></list-item-body></list-item></list></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_definition_list(self, input, output):
        self.do(input, output)

    data = [
        (
            ".. image:: images/biohazard.png",
            '<page><body><xinclude:include xinclude:href="wiki.local:images/biohazard.png" /></body></page>',
        ),
        (
            """.. image:: images/biohazard.png
    :height: 100
    :width: 200
    :scale: 50
    :alt: alternate text""",
            '<page><body><xinclude:include xhtml:alt="alternate text" xhtml:height="50" xhtml:width="100" xinclude:href="wiki.local:images/biohazard.png" /></body></page>',
        ),
        (
            "abc |test| cba\n\n.. |test| image:: test.png",
            '<page><body><p>abc <xinclude:include xhtml:alt="test" xinclude:href="wiki.local:test.png" /> cba</p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_image(self, input, output):
        self.do(input, output)

    data = [
        # from http://docutils.sourceforge.net/docs/user/rst/quickstart.html#sections; note first header is level 2 because same underlining was used for Chapter 2 Title
        (
            "Chapter 1 Title\n===============\n\nSection 1.1 Title\n-----------------\n\nSubsection 1.1.1 Title\n~~~~~~~~~~~~~~~~~~~~~~\n\nSection 1.2 Title\n-----------------\n\nChapter 2 Title\n===============\n",
            '<page><body><h outline-level="2">Chapter 1 Title</h><h outline-level="3">Section 1.1 Title</h><h outline-level="4">Subsection 1.1.1 Title</h><h outline-level="3">Section 1.2 Title</h><h outline-level="2">Chapter 2 Title</h></body></page>',
        ),
        # from http://docutils.sourceforge.net/docs/user/rst/quickstart.html#document-title-subtitle; note Subtitle and Section Title are level 2
        (
            "================\n Document Title\n================\n\n----------\n Subtitle\n----------\n\nSection Title\n=============",
            '<page><body><h outline-level="1">Document Title</h><h outline-level="2">Subtitle</h><h outline-level="2">Section Title</h></body></page>',
        ),
        # similar to test above; note that H3 is level 2, H4 is level 3, ...
        (
            "==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\n",
            '<page><body><h outline-level="1">H1</h><h outline-level="2">H2</h><h outline-level="2">H3</h><h outline-level="3">H4</h><h outline-level="4">H5</h><h outline-level="5">H6</h></body></page>',
        ),
        # adding a H2a heading using the H2 style underlining results in "normal" heading levels: H1 is a title, h2 and all other headings are sections
        (
            "==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\nH2a\n===\n\n",
            '<page><body><h outline-level="1">H1</h><h outline-level="2">H2</h><h outline-level="3">H3</h><h outline-level="4">H4</h><h outline-level="5">H5</h><h outline-level="6">H6</h><h outline-level="2">H2a</h></body></page>',
        ),
        # when a document starts with a paragraph, then the first heading is rendered as a section level 2 heading
        (
            "Paragraph\n\n==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\n",
            '<page><body><p>Paragraph</p><h outline-level="2">H1</h><h outline-level="3">H2</h><h outline-level="4">H3</h><h outline-level="5">H4</h><h outline-level="6">H5</h></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_headers(self, input, output):
        """
        reST has a unique method of defining heading levels.

        Depending on sequence of headings and reuse of heading underlining, then the docutils parser returns
        nodes to the moin2 rst_in parser as either a:
            * title
            * subtitle
            * section, then again as title
        where title and subtitle are similar to the left and right headings on pages of a book,
        but this usage is lost on html pages.

        The result is heading levels have unexpected values:
            * title, subtitle, section, subsection... (then subtitle and section are rendered as h2, subsection is h3)
            * <paragraph>, section, subsection... (then section is an h2, subsection is h3)
        """
        self.do(input, output)

    data = [
        (
            "Abra [1]_\n\n.. [1] arba",
            '<page><body><p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p></body></page>',
        ),
        (
            "Abra [#]_\n\n.. [#] arba",
            '<page><body><p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_footnote(self, input, output):
        self.do(input, output)

    data = [
        (
            ":Date: 2001-08-16\n:Version: 1\n:Authors: Joe Doe",
            "<page><body><table><table-body>2001-08-16<table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1</table-cell></table-row><table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Joe Doe</table-cell></table-row></table-body></table></body></page>",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_field_list(self, input, output):
        self.do(input, output)

    data = [
        (
            "Abra test_ arba\n\n.. _test: http://python.org",
            '<page><body><p>Abra <a xlink:href="http://python.org">test</a> arba</p></body></page>',
        ),
        (
            "Abra test__ arba\n\n.. __: http://python.org/fish/",
            '<page><body><p>Abra <a xlink:href="http://python.org/fish/">test</a> arba</p></body></page>',
        ),
        (
            "Abra test__ arba\n\n.. __: http://python.org",
            '<page><body><p>Abra <a xlink:href="http://python.org">test</a> arba</p></body></page>',
        ),
        (
            "Abra\n\n.. _example:\n\nAbra example_ arba\n",
            '<page><body><p>Abra</p><span id="example" /><p>Abra <a xlink:href="wiki.local:#example">example</a> arba</p></body></page>',
        ),
        (
            "Abra example_ arba\n\n.. _example:\n\ntext",
            '<page><body><p>Abra <a xlink:href="wiki.local:#example">example</a> arba</p><span id="example" /><p>text</p></body></page>',
        ),
        (
            "http://www.python.org/",
            '<page><body><p><a xlink:href="http://www.python.org/">http://www.python.org/</a></p></body></page>',
        ),
        ("http:Home", '<page><body><p><a xlink:href="wiki.local:Home">http:Home</a></p></body></page>'),
        ("`Home <http:Home>`_", '<page><body><p><a xlink:href="wiki.local:Home">Home</a></p></body></page>'),
        (
            "mailto:me@moin.com",
            '<page><body><p><a xlink:href="mailto:me@moin.com">mailto:me@moin.com</a></p></body></page>',
        ),
        (
            "`email me <mailto:fred@example.com>`_",
            '<page><body><p><a xlink:href="mailto:fred@example.com">email me</a></p></body></page>',
        ),
        (
            "`Write to me`_ with your questions.\n\n.. _Write to me: jdoe@example.com",
            '<page><body><p><a xlink:href="mailto:jdoe@example.com">Write to me</a> with your questions.</p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (".. macro:: <<TableOfContents()>>", "<page><body><table-of-content /></body></page>"),
        (".. macro:: <<Macro()>>", '<page><body><inline-part content-type="x-moin/macro;name=Macro" /></body></page>'),
        (
            ".. macro:: Macro(arg)",
            '<page><body><inline-part content-type="x-moin/macro;name=Macro"><arguments>arg</arguments></inline-part></body></page>',
        ),
        (
            "test |a| test\n\n.. |a| macro:: <<Macro()>>",
            '<page><body><p>test <inline-part content-type="x-moin/macro;name=Macro" /> test</p></body></page>',
        ),
        (".. contents::\n  :depth: 1\n", '<page><body><table-of-content outline-level="1" /></body></page>'),
        (
            ".. parser:: python test=test\n  import test\n  test.s = 11",
            '<page><body><part content-type="x-moin/format;name=python"><arguments><argument name="test">test</argument></arguments>import test\ntest.s = 11</part></body></page>',
        ),
        (
            ".. include:: RecentChanges",
            '<page><body><xinclude:include alt="&lt;&lt;Include(RecentChanges)&gt;&gt;" content-type="x-moin/macro;name=Include" xinclude:href="wiki.local:RecentChanges" /></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_directive(self, input, output):
        self.do(input, output)

    data = [
        (
            "+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n",
            '<page><body><table><table-body><table-row><table-cell><p>A</p></table-cell><table-cell><p>B</p></table-cell><table-cell number-rows-spanned="2"><p>D</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>C</p></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n",
            "<page><body><table><table-body><table-row><table-cell><p><strong>A</strong></p></table-cell><table-cell><p><strong>B</strong></p></table-cell><table-cell><p><strong>C</strong></p></table-cell></table-row><table-row><table-cell><p>1</p></table-cell><table-cell><p>2</p></table-cell><table-cell><p>3</p></table-cell></table-row></table-body></table></body></page>",
        ),
        (
            """+--------------------+-------------------------------------+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""",
            '<page><body><table><table-body><table-row><table-cell number-rows-spanned="2"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            """
+--------------------+-------------------------------------+
| AAAAAAAAAAAAAAAAAA | BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB |
+====================+=====================================+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""",
            '<page><body><table><table-header><table-row><table-cell><p>AAAAAAAAAAAAAAAAAA</p></table-cell><table-cell><p>BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB</p></table-cell></table-row></table-header><table-body><table-row><table-cell number-rows-spanned="2"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row></table-body></table></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            ":Author: Test\n:Version:  $Revision: 1.17 $\n:Copyright: c\n:Test: t",
            "<page><body><table><table-body><table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Test</table-cell></table-row><table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1.17</table-cell></table-row><table-row><table-cell><strong>Copyright:</strong></table-cell><table-cell>c</table-cell></table-row><table-row><table-cell><strong>Test:</strong></table-cell><table-cell><p>t</p></table-cell></table-row></table-body></table></body></page>",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_docutils_feature(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input, "text/x-rst;charset=utf-8", **args)
        assert self.serialize_strip(out) == output


coverage_modules = ["moin.converters.rst_in"]
