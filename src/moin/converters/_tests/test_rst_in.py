# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.converters.rst_in tests.
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
        ("paragraph", "<p>paragraph</p>"),
        ("line 1\nline 2", "<p>line 1\nline 2</p>"),
        ("paragraph 1\n\nparagraph\n2", "<p>paragraph 1</p><p>paragraph\n2</p>"),
        ("**Text**", "<p><strong>Text</strong></p>"),
        ("*Text*", "<p><emphasis>Text</emphasis></p>"),
        ("``Text``", "<p><code>Text</code></p>"),
        ("a _`Link`", '<p>a <span id="link">Link</span></p>'),
        ("thematic\n\n~~~~~\n\nbreak", '<p>thematic</p><separator xhtml:class="moin-hr2" /><p>break</p>'),
        (".. comment", '<div class="comment dashed">comment</div>'),
        ("..\n comment", '<div class="comment dashed">comment</div>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    # Interpreted text roles
    data = [
        # standard roles:
        (":abbreviation:`abbr.`", '<p><span xhtml:class="abbr">abbr.</span></p>'),
        (":ac:`DC`", '<p><span xhtml:class="abbr">DC</span></p>'),
        (r":code:`y = exp(x)`", r'<p><code xhtml:class="code">y = exp(x)</code></p>'),
        (r":literal:`% \ `", "<p><code>% </code></p>"),
        (r":math:`\sin(x)`", r"<p>\sin(x)</p>"),  # TODO: properly support mathematical content
        (":RFC:`1234`", '<p><a xlink:href="https://tools.ietf.org/html/rfc1234.html">RFC 1234</a></p>'),
        (":PEP:`01`", '<p><a xlink:href="https://peps.python.org/pep-0001">PEP 01</a></p>'),
        ("H\\ :sub:`2`\\ O", '<p>H<span baseline-shift="sub">2</span>O</p>'),
        ("E = mc\\ :sup:`2`", '<p>E = mc<span baseline-shift="super">2</span></p>'),
        (":title-reference:`Hamlet`", '<p><span xhtml:class="cite">Hamlet</span></p>'),
        (  # custom role using a CSS class
            ".. role:: orange\n\n:orange:`colourful` text",
            '<p><span xhtml:class="orange">colourful</span> text</p>',
        ),
        (  # special custom roles for <del> and <ins>
            ".. role:: del\n.. role:: ins\n\n:del:`deleted` text :ins:`inserted` text",
            "<p><del>deleted</del> text <ins>inserted</ins> text</p>",
        ),
        (  # custom role derived from "code" with syntax highlight
            '.. role:: python(code)\n   :language: python\n\nInline code like :python:`print(3*"Hurra!")`.',
            '<p>Inline code like <code xhtml:class="code python">'
            '<span xhtml:class="nb">print</span><span xhtml:class="p">(</span>'
            '<span xhtml:class="mi">3</span><span xhtml:class="o">*</span>'
            '<span xhtml:class="s2">"Hurra!"</span><span xhtml:class="p">)</span>'
            "</code>.</p>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_roles(self, input, output):
        self.do(input, output)

    # Lists and line blocks
    data = [
        (
            "1. a\n   b\n   c\n\n2. b\n\n   d",
            '<list item-label-generate="ordered">'
            "<list-item><list-item-body><p>a\nb\nc</p></list-item-body></list-item>"
            "<list-item><list-item-body><p>b</p><p>d</p></list-item-body></list-item>"
            "</list>",
        ),
        (
            "1. a\n2. b\n\nA. c\n\na. A\n\n   1. B\n\n   2. C\n\n",
            '<list item-label-generate="ordered"><list-item><list-item-body><p>a</p></list-item-body></list-item><list-item><list-item-body><p>b</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body><p>c</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body><p>A</p><list item-label-generate="ordered"><list-item><list-item-body><p>B</p></list-item-body></list-item><list-item><list-item-body><p>C</p></list-item-body></list-item></list></list-item-body></list-item></list>',
        ),
        (
            "* A\n\n   - B\n\n      + C\n\n   - D\n\n* E",
            '<list item-label-generate="unordered"><list-item><list-item-body><p>A</p><blockquote><list item-label-generate="unordered"><list-item><list-item-body><p>B</p><blockquote><list item-label-generate="unordered"><list-item><list-item-body><p>C</p></list-item-body></list-item></list></blockquote></list-item-body></list-item><list-item><list-item-body><p>D</p></list-item-body></list-item></list></blockquote></list-item-body></list-item><list-item><list-item-body><p>E</p></list-item-body></list-item></list>',
        ),
        (
            "what\n      def\n\nhow\n      to",
            "<list><list-item><list-item-label>what</list-item-label><list-item-body><p>def</p></list-item-body></list-item><list-item><list-item-label>how</list-item-label><list-item-body><p>to</p></list-item-body></list-item></list>",
        ),
        # nested in a block-quote and starting with a value other than 1
        (
            " 3. A\n #. B",
            '<blockquote><list item-label-generate="ordered" list-start="3"><list-item><list-item-body><p>A</p>'
            "</list-item-body></list-item><list-item><list-item-body><p>B</p></list-item-body></list-item></list>"
            "</blockquote>",
        ),
        ("| line 1\n| line2", "<line-block><line-blk>line 1</line-blk><line-blk>line2</line-blk></line-block>"),
        (
            "| line 1\n|  nested line-block",
            "<line-block><line-blk>line 1</line-blk><line-block><line-blk>nested line-block</line-blk></line-block></line-block>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            "term 1\n definition 1",
            "<list><list-item><list-item-label>term 1</list-item-label><list-item-body><p>definition 1</p></list-item-body></list-item></list>",
        ),
        (
            "term 2 : classifier 1 : classifier 2\n definition 2",
            "<list><list-item><list-item-label>term 2<span>:classifier 1</span><span>:classifier 2</span></list-item-label>classifier 1classifier 2<list-item-body><p>definition 2</p></list-item-body></list-item></list>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_definition_list(self, input, output):
        self.do(input, output)

    data = [
        (".. image:: images/biohazard.png", '<xinclude:include xinclude:href="wiki.local:images/biohazard.png" />'),
        (
            """
.. image:: images/biohazard.png
    :name: biohazard-logo
    :height: 100
    :width: 200
    :scale: 50
    :alt: alternate text""",
            '<span id="biohazard-logo" /><xinclude:include xhtml:alt="alternate text" xhtml:height="50" xhtml:width="100" xinclude:href="wiki.local:images/biohazard.png" />',
        ),
        (
            "abc |test| cba\n\n.. |test| image:: test.png",
            '<p>abc <xinclude:include xhtml:alt="test" xinclude:href="wiki.local:test.png" /> cba</p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_image(self, input, output):
        self.do(input, output)

    data = [
        # Leading headings become page title and subtitle (if the adornment style is unique).
        (
            "================\n Heading 1\n================\n\n"
            "Heading 2\n=========\n\n"
            "Heading 3\n---------\n\n"
            "Heading 4\n*********\n\n"
            "Heading 5\n:::::::::\n\n"
            "Heading 6\n+++++++++\n",
            '<h outline-level="1">Heading 1</h>'
            '<p xhtml:class="moin-subheading">Heading 2</p>'
            '<h outline-level="2">Heading 3</h>'
            '<h outline-level="3">Heading 4</h>'
            '<h outline-level="4">Heading 5</h>'
            '<h outline-level="5">Heading 6</h>',
        ),
        # There is no sub-heading because the second adornment style is
        # re-used in heading 4
        (
            "===============\n Heading 1\n===============\n\n"
            "Heading 2\n---------\n\n"
            "Heading 3\n~~~~~~~~~\n\n"
            "Heading 4\n---------\n\n",
            '<h outline-level="1">Heading 1</h>'
            '<h outline-level="2">Heading 2</h>'
            '<h outline-level="3">Heading 3</h>'
            '<h outline-level="2">Heading 4</h>',
        ),
        # The first heading is level 2 and there is no sub-heading
        # because the first adornment style is re-used in heading 4
        (
            "===============\n Heading 1\n===============\n\n"
            "Heading 2\n---------\n\n"
            "Heading 3\n~~~~~~~~~\n\n"
            "=============\n Heading 4\n=============\n",
            '<h outline-level="2">Heading 1</h>'
            '<h outline-level="3">Heading 2</h>'
            '<h outline-level="4">Heading 3</h>'
            '<h outline-level="2">Heading 4</h>',
        ),
        # The first heading is level 1, because underline+overline adornment
        # style differs from underline-only (even if the same char is used).
        (
            "===============\n Heading 1\n===============\n\n"
            "Heading 2\n---------\n\n"
            "Heading 3\n~~~~~~~~~\n\n"
            "Heading 4\n=============\n",
            '<h outline-level="1">Heading 1</h>'
            '<p xhtml:class="moin-subheading">Heading 2</p>'
            '<h outline-level="2">Heading 3</h>'
            '<h outline-level="3">Heading 4</h>',
        ),
        # When the first heading is preceded by visible content,
        # the first heading is a section heading (level 2).
        (
            "Paragraph\n\n"
            "================\n Heading 1\n================\n\n"
            "Heading 2\n=========\n\n"
            "Heading 3\n---------\n\n"
            "Heading 4\n*********\n\n",
            "<p>Paragraph</p>"
            '<h outline-level="2">Heading 1</h>'
            '<h outline-level="3">Heading 2</h>'
            '<h outline-level="4">Heading 3</h>'
            '<h outline-level="5">Heading 4</h>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_headers(self, input, output):
        """
        reST has a unique method of defining heading levels.

        Leading headings may become a page title and subtitle,
        but only if the adornment style is unique.

        See https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#document-structure
        """
        self.do(input, output)

    data = [
        ("Abra [1]_\n\n.. [1] arba", '<p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p>'),
        ("Abra [#]_\n\n.. [#] arba", '<p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_footnote(self, input, output):
        self.do(input, output)

    # Field Lists, Option Lists:
    # TODO: currently rendered as table (like Docutils html4css1 writer),
    #       use a description-list instead (like Docutils html5 writer)?
    data = [
        (
            "Leading text\n\n:Last Changed: 2001-08-16\n:*Version*: 1\n:Name: Joe Doe",
            "<p>Leading text</p>"
            '<table xhtml:class="moin-rst-fieldlist"><table-body>'
            "<table-row><table-cell><strong>Last Changed:</strong></table-cell>"
            "<table-cell><p>2001-08-16</p></table-cell></table-row>"
            "<table-row><table-cell><strong><emphasis>Version</emphasis>:</strong></table-cell>"
            "<table-cell><p>1</p></table-cell></table-row>"
            "<table-row><table-cell><strong>Name:</strong></table-cell>"
            "<table-cell><p>Joe Doe</p></table-cell></table-row>"
            "</table-body></table>",
        ),
        # A field list at the start of a page is transformed into a "docinfo"
        # bibliographic data (visible meta-data)
        (
            ":Date: 2001-08-16\n:Author: Joe Doe\n:Version:  $Revision: 1.17 $\n",
            '<table xhtml:class="moin-rst-fieldlist"><table-body>'
            "<table-row><table-cell><strong>Date:</strong></table-cell><table-cell>2001-08-16</table-cell></table-row>"
            "<table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Joe Doe</table-cell></table-row>"
            "<table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1.17</table-cell></table-row>"
            "</table-body></table>",
        ),
        (
            ":Authors: Pat, Patagon\n:Copyright: ©\n:Test: t",
            '<table xhtml:class="moin-rst-fieldlist"><table-body>'
            "<table-row><table-cell><strong>Authors:</strong></table-cell>"
            "<table-cell><p>Pat</p><p>Patagon</p></table-cell></table-row>"
            "<table-row><table-cell><strong>Copyright:</strong></table-cell><table-cell>©</table-cell></table-row>"
            '<table-row xhtml:class="test"><table-cell><strong>Test:</strong></table-cell>'
            "<table-cell><p>t</p></table-cell></table-row>"
            "</table-body></table>",
        ),
        # option list
        (
            "-a           Output all.\n"
            "--print arg  Output just arg.\n"
            "-f FILE, --file=FILE  These two options are synonyms;\n"
            "                      both have arguments.\n",
            '<table xhtml:class="moin-rst-optionlist"><table-body>'
            '<table-row><table-cell><span xhtml:class="kbd option">-a</span></table-cell>'
            "<table-cell><p>Output all.</p></table-cell></table-row>"
            '<table-row><table-cell><span xhtml:class="kbd option">--print arg</span></table-cell>'
            "<table-cell><p>Output just arg.</p></table-cell></table-row>"
            '<table-row><table-cell><span xhtml:class="kbd option">-f FILE</span>, <span xhtml:class="kbd option">--file=FILE</span></table-cell>'
            "<table-cell><p>These two options are synonyms;\nboth have arguments.</p></table-cell></table-row>"
            "</table-body></table>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_field_list(self, input, output):
        self.do(input, output)

    data = [
        (
            "Abra test_ arba\n\n.. _test: http://python.org",
            '<p>Abra <a xlink:href="http://python.org">test</a> arba</p>',
        ),
        (
            "Abra test__ arba\n\n.. __: http://python.org/fish/",
            '<p>Abra <a xlink:href="http://python.org/fish/">test</a> arba</p>',
        ),
        ("Abra test__ arba\n\n.. __: http://python.org", '<p>Abra <a xlink:href="http://python.org">test</a> arba</p>'),
        (
            "Abra\n\n.. _example:\n\nAbra example_ arba\n",
            '<p>Abra</p><span id="example" /><p>Abra <a xlink:href="wiki.local:#example">example</a> arba</p>',
        ),
        (
            """
Abra example_ arba

.. _example:
.. _alias:

text""",
            '<p>Abra <a xlink:href="wiki.local:#example">example</a> arba</p><span id="alias" /><span id="example" /><p>text</p>',
        ),
        (  # A reference_ with no matching target links to a local Wiki item.
            "wiki references: `item`_, `namespace/item`_, `ns/item/subitem`_, `../sibling`_, `/subitem`_",
            '<p>wiki references: <a xlink:href="wiki.local:item">item</a>,'
            ' <a xlink:href="wiki.local:namespace/item">namespace/item</a>,'
            ' <a xlink:href="wiki.local:ns/item/subitem">ns/item/subitem</a>,'
            ' <a xlink:href="wiki.local:../sibling">../sibling</a>,'
            ' <a xlink:href="wiki.local:/subitem">/subitem</a></p>',
        ),
        (
            "`Whitespace  is\nnormalized\xA0& CÄSE is Kept.`_",
            '<p><a xlink:href="wiki.local:Whitespace%20is%20normalized%20&amp;%20CÄSE%20is%20Kept.">Whitespace  is\nnormalized\xA0&amp; CÄSE is Kept.</a></p>',
        ),
        (  # in rST, reference-name matching is case insensitive:
            "Chapter 1\n===============\n\nA reference to `chapter 1`_.\n",
            '<h outline-level="1">Chapter 1</h><p>A reference to <a xlink:href="wiki.local:#Chapter_1">chapter 1</a>.</p>',
        ),
        (  # check handling of non-ASCII chars:
            "τίτλος\n^^^^^^\n\nA reference to `τίτλος`_.\n",
            '<h outline-level="1">τίτλος</h><p>A reference to <a xlink:href="wiki.local:#A.2BA8QDrwPEA7sDvwPC-">τίτλος</a>.</p>',
        ),
        (
            "§ With % strange & siLLY <title>\n"
            "--------------------------------\n\n"
            "Reference to `§ With % strange\n"
            "& siLLY \\<title>`_.\n",
            '<h outline-level="1">§ With % strange &amp; siLLY &lt;title&gt;</h>'
            '<p>Reference to <a xlink:href="wiki.local:#A.2BAKc_With_.25_strange_.26_siLLY_.3Ctitle.3E">§ With % strange\n'
            "&amp; siLLY &lt;title&gt;</a>.</p>",
        ),
        ("http://www.python.org/", '<p><a xlink:href="http://www.python.org/">http://www.python.org/</a></p>'),
        ("http:Home", '<p><a xlink:href="wiki.local:Home">http:Home</a></p>'),
        ("`Home <http:Home>`_", '<p><a xlink:href="wiki.local:Home">Home</a></p>'),
        ("mailto:me@moin.com", '<p><a xlink:href="mailto:me@moin.com">mailto:me@moin.com</a></p>'),
        ("`email me <mailto:fred@example.com>`_", '<p><a xlink:href="mailto:fred@example.com">email me</a></p>'),
        (
            "`Write to me`_ with your questions.\n\n.. _Write to me: jdoe@example.com",
            '<p><a xlink:href="mailto:jdoe@example.com">Write to me</a> with your questions.</p>',
        ),
        (  # URI schemes not in the whitelist are interpreted as local wiki item names
            "`Text <javascript:alert('xss')>`_",
            """<p><a xlink:href="wiki.local:javascript:alert%28'xss'%29">Text</a></p>""",
        ),
    ]

    @pytest.mark.usefixtures("_app_ctx")
    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (".. macro:: <<TableOfContents()>>", "<table-of-content />"),
        (".. macro:: <<Macro()>>", '<inline-part content-type="x-moin/macro;name=Macro" />'),
        (
            ".. macro:: Macro(arg)",
            '<inline-part content-type="x-moin/macro;name=Macro"><arguments>arg</arguments></inline-part>',
        ),
        (
            "test |a| test\n\n.. |a| macro:: <<Macro()>>",
            '<p>test <inline-part content-type="x-moin/macro;name=Macro" /> test</p>',
        ),
        (".. contents::", "<table-of-content />"),
        (".. contents::\n  :depth: 1\n", '<table-of-content outline-level="1" />'),
        (
            ".. parser:: python test=test\n  import test\n  test.s = 11",
            '<part content-type="x-moin/format;name=python"><arguments><argument name="test">test</argument></arguments>import test\ntest.s = 11</part>',
        ),
        (  # modified: include (transclude) Wiki pages instead of files
            ".. include:: RecentChanges",
            '<xinclude:include alt="&lt;&lt;Include(RecentChanges)&gt;&gt;" content-type="x-moin/macro;name=Include" xinclude:href="wiki.local:RecentChanges" />',
        ),
        (  # rST standard definition files can still be included.
            ".. include:: <isonum.txt>\n\nR = 470 |Ohm|",
            '<div class="comment dashed">This data file has been placed in the public domain.</div>'
            '<div class="comment dashed">Derived from the Unicode character mappings available from\n'
            "&lt;http://www.w3.org/2003/entities/xml/&gt;.\n"
            "Processed by unicode2rstsubs.py, part of Docutils:\n"
            "&lt;https://docutils.sourceforge.io&gt;."
            "</div>"
            "<p>R = 470 Ω</p>",
        ),
        (".. meta::\n   :description lang=en: An amusing story", ""),  # TODO: handle metadata (which?, how?)
        (".. raw:: latex\n\n   potentially \\emph{harmfull} content", ""),  # ignore "foreign" formats
        (
            ".. raw:: html\n\n   <div>potentially harmfull content</div>",
            '<admonition type="error">'
            '<p xhtml:class="moin-title">System Message: ERROR/3 (rST input line 1) </p>'
            "<p>Raw HTML is not supported in Moin.</p>"
            "<blockcode>&lt;div&gt;potentially harmfull content&lt;/div&gt;</blockcode>"
            "</admonition>",
        ),
        (
            ".. role:: raw-html(raw)\n  :format: html\n\nParagraph with :raw-html:`potentially harmfull` inline HTML.",
            "<p>Paragraph with "
            '<admonition type="error">'
            '<p xhtml:class="moin-title">System Message: ERROR/3 (rST input line 4) </p>'
            "<p>Raw HTML is not supported in Moin.</p>"
            "<blockcode>potentially harmfull</blockcode>"
            "</admonition>"
            " inline HTML.</p>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_directive(self, input, output):
        self.do(input, output)

    data = [
        (
            "+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n",
            '<table><table-body><table-row><table-cell><p>A</p></table-cell><table-cell><p>B</p></table-cell><table-cell number-rows-spanned="2"><p>D</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>C</p></table-cell></table-row></table-body></table>',
        ),
        (
            "+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n",
            "<table><table-body><table-row><table-cell><p><strong>A</strong></p></table-cell><table-cell><p><strong>B</strong></p></table-cell><table-cell><p><strong>C</strong></p></table-cell></table-row><table-row><table-cell><p>1</p></table-cell><table-cell><p>2</p></table-cell><table-cell><p>3</p></table-cell></table-row></table-body></table>",
        ),
        (
            """
+--------------------+-------------------------------------+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""",
            '<table><table-body><table-row><table-cell number-rows-spanned="2"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row></table-body></table>',
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
            '<table><table-header><table-row><table-cell><p>AAAAAAAAAAAAAAAAAA</p></table-cell><table-cell><p>BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB</p></table-cell></table-row></table-header><table-body><table-row><table-cell number-rows-spanned="2"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row><table-row><table-cell number-columns-spanned="2"><p>test</p></table-cell></table-row></table-body></table>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        # admonitions (hint, info, warning, error, ...)
        (
            '.. note::\n   :name: note-id\n\n   An admonition of type "note"',
            '<span id="note-id" /><admonition type="note"><p>An admonition of type "note"</p></admonition>',
        ),
        # use an attention for a generic admonition
        (
            ".. admonition:: Generic Admonition\n\n   Be alert!",
            '<admonition type="attention" xhtml:class="admonition-generic-admonition">'
            '<p xhtml:class="moin-title">Generic Admonition</p>'
            "<p>Be alert!</p></admonition>",
        ),
        # Moin uses admonitions also for system messages
        (
            "Unbalanced *inline markup.",
            '<p>Unbalanced <span id="problematic-1" /><a xhtml:class="red" xlink:href="#system-message-1">*</a>inline markup.</p>'
            '<span id="system-message-1" /><admonition type="caution">'
            '<p xhtml:class="moin-title">System Message: WARNING/2 (rST input line 1) '
            '<span id="system-message-1" /><a xlink:href="#problematic-1">backlink</a></p>'
            "<p>Inline emphasis start-string without end-string.</p>"
            "</admonition>",
        ),
        # TODO: this currently fails because the parsing error is not cleared.
        # (
        #     "Sections must not be nested in body elements.\n\n"
        #     "  not allowed\n"
        #     "  -----------\n",
        #     "<p>Sections must not be nested in body elements.</p><blockquote>"
        #     '<admonition type="error"><p xhtml:class="moin-title">System Message: ERROR/3 (rST input line 4)</p>'
        #     "<p>Unexpected section title.</p>"
        #     "<blockcode>not allowed\n-----------</blockcode>"
        #     "</admonition></blockquote>"
        # )
        # Topics, Sidebars, and Rubrics
        (
            ".. topic:: Topic Title\n   :class: custom\n\n   topic content",
            '<div xhtml:class="html-aside custom"><p xhtml:class="moin-title">Topic Title</p><p>topic content</p></div>',
        ),
        (
            ".. sidebar:: Sidebar Title\n   :subtitle: Sidebar Subtitle\n   :class: float-right\n\n   sidebar content",
            '<div xhtml:class="html-aside rst-sidebar float-right">'
            '<p xhtml:class="moin-title">Sidebar Title</p>'
            '<p xhtml:class="moin-subheading">Sidebar Subtitle</p>'
            "<p>sidebar content</p></div>",
        ),
        (
            ".. rubric:: Informal Heading\n  :class: custom",
            '<p xhtml:class="moin-title moin-rubric custom">Informal Heading</p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_docutils_feature(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        result = self.output_re.sub("", result)
        if result == "<page><body /></page>":  # empty document
            return ""
        result = result.removeprefix("<page><body>")
        result = result.removesuffix("</body></page>")
        return result

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input, "text/x-rst;charset=utf-8", **args)
        assert self.serialize_strip(out) == output


coverage_modules = ["moin.converters.rst_in"]
