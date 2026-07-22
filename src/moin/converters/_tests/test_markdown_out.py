# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.converters.markdown_out tests.
"""

import pytest

from emeraldtree import ElementTree as ET
from moin.converters import ElementException
from moin.converters.markdown_out import Converter
from moin.utils.render import RenderContext
from moin.utils.tree import html, moin_page, xlink, xml, xinclude
from . import XMLNS_RE, TAGSTART_RE


class Base:
    input_namespaces = ns_all = (
        f'xmlns="{moin_page}" xmlns:page="{moin_page}" xmlns:html="{html}" xmlns:xlink="{xlink}" xmlns:xml="{xml}" xmlns:xinclude="{xinclude}"'
    )
    output_namespaces = {moin_page: "page"}

    render_context = RenderContext(allow_style_attributes=True, use_nonces=False, convert_inline_style=False)

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter(self.render_context)

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i.encode("utf-8"))

    def handle_output(self, elem, **options):
        return elem

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        # assert self.handle_output(out) == output
        assert self.handle_output(out).strip() == output.strip()


class TestConverter(Base):

    data = [
        ("<page:p>Text</page:p>", "Text\n"),
        ("<page:strong>bold</page:strong>", "**bold**"),
        ("<page:emphasis>em</page:emphasis>", "*em*"),
        ("<page:code>code</page:code>", "`code`"),
        ("<page:separator />", "\n----\n"),
        ("<page:tag><page:line-break /></page:tag>", "<br />"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            "* A\n",
        ),
        (
            '<page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            "1. A\n",
        ),
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>',
            '* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F{: list-style-type="upper-roman"}\n',
        ),
        (
            "<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>",
            " \nA\n:: B\n:: C\n:: D\n",
        ),
        (
            '<page:list page:item-label-generate="ordered" page:list-start="5"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            '1.#5 A{: list-start="5"}',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:table><page:table-body><page:table-row><page:span>Header 1</page:span><page:span>Header 2</page:span></page:table-row><page:table-row><page:span>Row 1, Cell 1</page:span><page:span>Row 1, Cell 2</page:span></page:table-row></page:table-body></page:table>",
            "\n|Header 1|Header 2|\n|----|----|\n|Row 1, Cell 1|Row 1, Cell 2|\n",
        ),
        (
            "<page:table><page:table-header><page:table-row><page:th>Head 1</page:th><page:th>Head 2</page:th></page:table-row></page:table-header></page:table>",
            "\n|Head 1|Head 2|\n|------|------|\n",
        ),  # Table with explicit header
        (
            "<page:table><page:table-body><page:table-row><page:span>Cell 1</page:span><page:span>Cell 2</page:span></page:table-row></page:table-body></page:table>",
            "\n|Cell 1|Cell 2|\n|----|----|\n",
        ),
    ]  # body only

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:blockcode>def helper():\n    return True</page:blockcode>",
            "\n\n    def helper():\n        return True\n\n",
        ),
        (
            '<page:blockcode html:class="codehilite">Already highlighted text</page:blockcode>',
            "Already highlighted text",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_block_code(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:page><page:block-comment>This is a comment line</page:block-comment></page:page>",
            "<!-- This is a comment line -->",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_block_comment(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:page><page:blockquote>This is first line\n This is second line\n This is third line</page:blockquote></page:page>",
            "\n > This is first line\n >  This is second line\n >  This is third line\n",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_block_quote(self, input, output):
        self.do(input, output)

    data = [
        ('<page:div html:class="toc"><page:p>Contents</page:p></page:div>', "\n\n[TOC]\n\n"),  # just toc
        (
            '<page:div html:class="codehilite"><page:tag><page:span>x</page:span>Hello World\n </page:tag></page:div>',
            "\n   Hello World\n",
        ),  # codehilite
        (
            '<page:div html:class="warning"><page:p>This is a warning message.</page:p></page:div>',
            "\n\nThis is a warning message.\n\n",
        ),  # without codehilite,
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_div(self, input, output):
        self.do(input, output)

    data = [
        ('<page:h page:outline-level="2"><page:p>Heading</page:p></page:h>', "## Heading ##"),
        ('<page:h page:outline-level="4"><page:p>Heading</page:p></page:h>', "#### Heading ####"),
        ('<page:h page:outline-level="0"><page:p>Heading</page:p></page:h>', "# Heading #"),  # edgecase
        ('<page:h page:outline-level="8"><page:p>Heading</page:p></page:h>', "###### Heading ######"),  # edge case
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_page_h(self, input, output):
        self.do(input, output)

    def test_heading_invalid_level(self):
        with pytest.raises(ElementException):
            self.conv(self.handle_input('<page:h page:outline-level="abc"><page:p>Heading</page:p></page:h>'))

    data = [
        (
            '<page:p html:class="warning-box" html:id="alert-1"></page:p>',
            '{: class="warning-box" id="alert-1"}',
        ),  # normal attributes
        (
            '<page:tag><page:h page:outline-level="3" page:data-lineno="42"></page:h></page:tag>',
            "###  ###",
        ),  # data-lineno
        ('<page:p html:href="http://google.com" html:class="info">Text</page:p>', 'Text\n{: class="info"}\n'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_attribute_list(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:object xlink:href="/+get/+/my_image.png" html:title="A nice picture">This is the alt text</page:object>',
            '![This is the alt text](/+get/+/my_image.png "A nice picture")',
        ),
        (
            '<page:object xinclude:href="wiki.local:SomeOtherPage" html:alt="Default alt"></page:object>',
            "![Default alt](SomeOtherPage)",
        ),  # internal
        ('<page:object html:title="Title Alone">Title</page:object>', '![Title]( "Title Alone")'),  # with title
        (
            '<page:object xlink:href="/+get/+/my_image.png" html:alt="Alt text"></page:object>',
            "![Alt text](/+get/+/my_image.png)",
        ),  # image with alt
        ('<page:object xlink:href="image.png"></page:object>', "![](image.png)"),  # href
        ('<page:object xlink:href="wiki.local:SomePage"></page:object>', "![](SomePage)"),
        (
            '<page:object xlink:href="photo.jpg" html:alt="A photo"><page:span>ignored</page:span></page:object>',
            "![A photo](photo.jpg)",
        ),
        (
            '<page:object xlink:href="/+get/+abcdef/audio.mp3" html:data-href="/help-common/audio.mp3" '
            'html:alt="Audio" html:class="moin-transclusion"></page:object>',
            "![Audio](help-common/audio.mp3)",
        ),
        (
            '<page:object xlink:href="/+get/+abcdef/video.mp4" html:data-href="/help-common/video.mp4?do=show" '
            'html:alt="Video" html:class="moin-transclusion"></page:object>',
            "![Video](help-common/video.mp4)",
        ),
        (
            '<page:object xinclude:href="wiki.local:audio.mp3" html:data-href="/help-common/audio.mp3" '
            'html:alt="help-common/audio.mp3" html:class="moin-transclusion">'
            "Your Browser does not support HTML5 audio/video element.</page:object>",
            "![audio.mp3](help-common/audio.mp3)",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_page_object(self, input, output):
        self.do(input, output)

    data = [
        ('<page:p page:class="moin-error">Warning: Something failed.</page:p>', '{: class="moin-error"}'),  # moin error
        (
            "<page:table><page:table_row><page:table_cell><page:span>Some Before text</page:span><page:p>New Start</page:p></page:table_cell></page:table_row></page:table>",
            "|Some Before text<br />New Start|\n|----|",
        ),  # table with span
        (
            "<page:table><page:table-body><page:table-row><page:span>Some Before text</page:span></page:table-row><page:p>New Start</page:p></page:table-body></page:table>",
            "|Some Before text|\n|----|\nNew Start",
        ),  # table without span
        (
            "<page:list><page:list_item><page:span>Some Before text</page:span><page:p>New Start</page:p></page:list_item></page:list>",
            "Some Before text<br />New Start",
        ),  # list with span
        (
            "<page:list><page:list_item>Some Before text</page:list_item><page:p>New Start</page:p></page:list>",
            "Some Before textNew Start",
        ),  # list without span
        (
            "<page:page><page:p>This is the first paragraph.</page:p><page:p>This is the second paragraph.</page:p></page:page>",
            "This is the first paragraph.\n\nThis is the second paragraph.",
        ),  # para after text
        (
            "<page:page><page:strong>Bold text</page:strong><page:p>Paragraph after bold</page:p></page:page>",
            "**Bold text**\nParagraph after bold",
        ),
    ]  # para after heading so one newline

    @pytest.mark.parametrize("input,output", data)
    def test_page_p(self, input, output):
        self.do(input, output)

    data = [
        ('<a xlink:href="www.google.com">Google Site</a>', "[Google Site](www.google.com)"),  # with href
        (
            '<a xlink:href="www.google.com" html:title="Google Site"></a>',
            '[](www.google.com "Google Site")',
        ),  # with title
        (
            '<a xlink:href="www.google.com" page:class="site-link"></a>',
            '[](www.google.com){:class="site-link"}',
        ),  # with title and class
        ('<a xlink:href="wiki.local:/HelpContents">Help</a>', "[Help](/HelpContents)"),
    ]  # internal

    @pytest.mark.parametrize("input,output", data)
    def test_page_a(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:p>Some text<page:note page:note-class="footnote">This is a footnote</page:note></page:p></page:page>',
            'Some text[^1]{: note-class="footnote"}\n\n\n[^1]: This is a footnote',
        ),  # footnote
        (
            "<page:page><page:p>Some text<page:note>This is a footnote</page:note></page:p></page:page>",
            "Some text",
        ),  # no footnote
        (
            '<page:page><page:p>Some text<page:note page:note-class="other">This is a note</page:note></page:p></page:page>',
            'Some text{: note-class="other"}',
        ),
    ]  # other class

    @pytest.mark.parametrize("input,output", data)
    def test_page_note(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:blockcode>def helper():\n    return True</page:blockcode>",
            "    def helper():\n        return True\n",
        ),  # with codeblock
        (
            "<page:nowiki><page:code>some random code</page:code></page:nowiki>",
            "`some random code`",
        ),  # without codeblock
        ("<page:nowiki>plain text</page:nowiki>", "plain text"),
    ]  # with text

    @pytest.mark.parametrize("input,output", data)
    def test_page_nowiki(self, input, output):
        self.do(input, output)

    data = [
        ("<page:del>removed text</page:del>", "<del>removed text</del>"),
        ("<page:sup>1</page:sup>", "<sup>1</sup>"),
        ("<page:sub>a</page:sub>", "<sub>a</sub>"),
        ("<page:s>S</page:s>", "<s>S</s>"),
        ("<page:quote>quoted text</page:quote>", "<q>quoted text</q>"),
        ("<page:u>underlined</page:u>", "<u>underlined</u>"),
        ("<page:literal>monospace</page:literal>", '<span class="monospaced">monospace</span>'),
        ('<page:emphasis page:html-tag="i">italic text</page:emphasis>', "<i>italic text</i>"),
        ('<page:span page:html-tag="mark">highlighted</page:span>', "<mark>highlighted</mark>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_html_inline(self, input, output):
        self.do(input, output)

    data = [("<page:page><page:table-of-content /></page:page>", "\n[TOC]\n")]

    @pytest.mark.parametrize("input,output", data)
    def test_table_contents(self, input, output):
        self.do(input, output)

    data = [('<xinclude:include xinclude:href="wiki.local:SomePage" />', "![](SomePage)")]

    @pytest.mark.parametrize("input,output", data)
    def test_xinclude(self, input, output):
        self.do(input, output)

    data = [('<page:span html:class="custom">styled</page:span>', '<span class="custom">styled</span>')]

    @pytest.mark.parametrize("input,output", data)
    def test_span(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:table><page:table-header><page:table-row><page:th page:style="text-align: center;">H1</page:th></page:table-row></page:table-header></page:table>',
            "\n|H1|\n|:----:|\n",
        ),  # center
        (
            '<page:table><page:table-header><page:table-row><page:th page:style="text-align: left;">H1</page:th></page:table-row></page:table-header></page:table>',
            "\n|H1|\n|:-----|\n",
        ),  # left
        (
            '<page:table><page:table-header><page:table-row><page:th page:style="text-align: right;">H1</page:th></page:table-row></page:table-header></page:table>',
            "\n|H1|\n|-----:|\n",
        ),
    ]  # right

    @pytest.mark.parametrize("input,output", data)
    def test_table_header(self, input, output):
        self.do(input, output)
