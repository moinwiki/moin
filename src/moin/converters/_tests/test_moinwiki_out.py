# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.moinwiki_out
"""

import pytest

from emeraldtree import ElementTree as ET

from . import XMLNS_RE, TAGSTART_RE

from moin.utils.tree import html, moin_page, xlink
from moin.converters.moinwiki_out import Converter


class Base:
    input_namespaces = ns_all = 'xmlns="{}" xmlns:page="{}" xmlns:xlink="{}" xmlns:html="{}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, html.namespace
    )
    output_namespaces = {moin_page.namespace: "page"}

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i.encode("utf-8"))

    def handle_output(self, elem, **options):
        return elem

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        # assert self.handle_output(out) == output
        assert (
            self.handle_output(out).strip() == output.strip()
        )  # TODO: remove .strip() when number of \n between blocks in moinwiki_out.py is stable


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        ("<page:p>Текст</page:p>", "Текст\n"),
        ("<page:p>Text</page:p>", "Text\n"),
        ("<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", "Text\n\nText\n"),
        ("<page:separator />", "----\n"),
        ("<page:strong>strong</page:strong>", "'''strong'''"),
        ("<page:emphasis>emphasis</page:emphasis>", "''emphasis''"),
        ("<page:blockcode>blockcode</page:blockcode>", "{{{\nblockcode\n}}}\n"),
        ("<page:code>monospace</page:code>", "`monospace`"),
        ("<page:del>stroke</page:del>", "--(stroke)--"),
        ("<page:ins>underline</page:ins>", "__underline__"),
        ('<page:span page:font-size="120%">larger</page:span>', "~+larger+~"),
        ('<page:span page:font-size="85%">smaller</page:span>', "~-smaller-~"),
        ('<page:tag><page:span page:baseline-shift="super">super</page:span>script</page:tag>', "^super^script"),
        ('<page:tag><page:span page:baseline-shift="sub">sub</page:span>script</page:tag>', ",,sub,,script"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:a xlink:href="wiki.local:SomePage#subsection">subsection of Some Page</page:a>',
            "[[SomePage#subsection|subsection of Some Page]]",
        ),
        (
            '<page:a html:target="_blank" xlink:href="wiki.local:SomePage">{{attachment:samplegraphic.png}}</page:a>',
            '[[SomePage|{{attachment:samplegraphic.png}}|target="_blank"]]',
        ),
        (
            '<page:a xlink:href="wiki.local:SomePage?target=_blank">{{attachment:samplegraphic.png}}</page:a>',
            "[[SomePage?target=_blank|{{attachment:samplegraphic.png}}]]",
        ),
        (
            '<page:a html:target="_blank" xlink:href="wiki.local:SomePage">{{/samplegraphic.png}}</page:a>',
            '[[SomePage|{{/samplegraphic.png}}|target="_blank"]]',
        ),
        ('<page:a xlink:href="../SisterPage">link text</page:a>', "[[../SisterPage|link text]]"),
        (
            '<page:a html:target="_blank" html:class="aaa" xlink:href="http://static.moinmo.in/logos/moinmoin.png">{{attachment:samplegraphic.png}}</page:a>',
            '[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|class="aaa",target="_blank"]]',
        ),
        (
            '<page:a html:class="green dotted" html:accesskey="1" xlink:href="http://moinmo.in/">MoinMoin Wiki</page:a>',
            '[[http://moinmo.in/|MoinMoin Wiki|accesskey="1",class="green dotted"]]',
        ),
        (
            '<page:a xlink:href="MoinMoin:MoinMoinWiki?action=diff&amp;rev1=1&amp;rev2=2">MoinMoin Wiki</page:a>',
            "[[MoinMoin:MoinMoinWiki?action=diff&rev1=1&rev2=2|MoinMoin Wiki]]",
        ),
        (
            '<page:a xlink:href="attachment:HelpOnImages/pineapple.jpg?do=get">a pineapple</page:a>',
            "[[attachment:HelpOnImages/pineapple.jpg?do=get|a pineapple]]",
        ),
        (
            '<page:a xlink:href="attachment:filename.txt">attachment:filename.txt</page:a>',
            "[[attachment:filename.txt]]",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:object xlink:href="http://static.moinmo.in/logos/moinmoin.png" />',
            "{{http://static.moinmo.in/logos/moinmoin.png}}",
        ),
        (
            '<page:object page:alt="alt text" xlink:href="http://static.moinmo.in/logos/moinmoin.png">alt text</page:object>',
            "{{http://static.moinmo.in/logos/moinmoin.png|alt text}}",
        ),
        ('<page:object xlink:href="attachment:image.png" />', "{{attachment:image.png}}"),
        (
            '<page:object page:alt="alt text" xlink:href="attachment:image.png">alt text</page:object>',
            "{{attachment:image.png|alt text}}",
        ),
        (
            '<page:object xlink:href="attachment:image.png" html:width="100" html:height="150" html:class="left">alt text</page:object>',
            '{{attachment:image.png|alt text|class="left" height="150" width="100"}}',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_object(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            " * A\n",
        ),
        (
            '<page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            " 1. A\n",
        ),
        (
            '<page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            " I. A\n",
        ),
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>',
            " * A\n * B\n   1. C\n   1. D\n      I. E\n      I. F\n",
        ),
        (
            "<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>",
            " A::\n :: B\n :: C\n :: D\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned="2">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">C</page:table-cell></page:table-row></page:table-body></page:table>',
            '||A||B||<rowspan="2">D||\n||<colspan="2">C||\n',
        ),
        (
            "<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>",
            "||'''A'''||'''B'''||'''C'''||\n||1||2||3||\n",
        ),
        (
            '<page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned="2">cell spanning 2 rows</page:table-cell><page:table-cell>cell in the 2nd column</page:table-cell></page:table-row><page:table-row><page:table-cell>cell in the 2nd column of the 2nd row</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">test</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">test</page:table-cell></page:table-row></page:table-body></page:table>',
            '||<rowspan="2">cell spanning 2 rows||cell in the 2nd column||\n||cell in the 2nd column of the 2nd row||\n||<colspan="2">test||\n||<colspan="2">test||\n',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:note page:note-class="footnote"><page:note-body>test</page:note-body></page:note>',
            "<<FootNote(test)>>",
        ),
        ('<page:tag><page:table-of-content page:outline-level="2" /></page:tag>', "<<TableOfContents(2)>>\n"),
        (
            '<page:part page:alt="&lt;&lt;Anchor(anchorname)&gt;&gt;" page:content-type="x-moin/macro;name=Anchor"><page:arguments>anchorname</page:arguments></page:part>',
            "<<Anchor(anchorname)>>\n",
        ),
        (
            '<page:part page:alt="&lt;&lt;MonthCalendar(,,12)&gt;&gt;" page:content-type="x-moin/macro;name=MonthCalendar"><page:arguments>,,12</page:arguments></page:part>',
            "<<MonthCalendar(,,12)>>\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_macros(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:body><page:page><page:body page:class="comment dotted"><page:p>This is a wiki parser.</page:p><page:p>Its visibility gets toggled the same way.</page:p></page:body></page:page></page:body></page:page>',
            "{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}\n",
        ),
        (
            '<page:page><page:body><page:page><page:body page:class="red solid"><page:p>This is wiki markup in a <page:strong>div</page:strong> with <page:ins>css</page:ins> <page:code>class="red solid"</page:code>.</page:p></page:body></page:page></page:body></page:page>',
            "{{{#!wiki red/solid\nThis is wiki markup in a '''div''' with __css__ `class=\"red solid\"`.\n}}}\n",
        ),
        (
            '<page:page><page:body><page:part page:content-type="x-moin/format;name=creole"><page:arguments><page:argument page:name="style">st: er</page:argument><page:argument page:name="class">par: arg para: arga</page:argument></page:arguments><page:body>... **bold** ...</page:body></page:part></page:body></page:page>',
            '{{{#!creole(style="st: er" class="par: arg para: arga")\n... **bold** ...\n}}}\n',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_parser(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>",
            "A\n\nB\n\nC\n\nD\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell>A<page:line-break></page:line-break>B<page:line-break></page:line-break>C<page:line-break></page:line-break>D</page:table_cell></page:table_row></page:table></page:body></page:page>",
            "||A<<BR>>B<<BR>>C<<BR>>D||\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell>A<page:line-break></page:line-break>B<page:line-break></page:line-break>C<page:line-break></page:line-break>D</page:table_cell></page:table_row></page:table></page:body></page:page>",
            "||Z||A<<BR>>B<<BR>>C<<BR>>D||\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell>A<page:line-break></page:line-break>B<page:line-break></page:line-break>C<page:line-break></page:line-break>D</page:table_cell></page:table_row></page:table></page:body></page:page>",
            "||Z||\n||A<<BR>>B<<BR>>C<<BR>>D||\n",
        ),
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body>A<page:line-break></page:line-break>A</page:list-item-body></page:list-item><page:list-item><page:list-item-body>A<page:line-break></page:line-break>A<page:line-break></page:line-break>A</page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            " * A<<BR>>A\n * A<<BR>>A<<BR>>A\n * A\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_br(self, input, output):
        self.do(input, output)

    data = [
        ("<page:page><page:body><page:p>A</page:p><page:separator /></page:body></page:page>", "A\n----\n"),
        (
            '<page:page><page:body><page:p>A</page:p><page:separator page:class="moin-hr1"/></page:body></page:page>',
            "A\n----\n",
        ),
        (
            '<page:page><page:body><page:p>A</page:p><page:separator page:class="moin-hr3"/></page:body></page:page>',
            "A\n------\n",
        ),
        (
            '<page:page><page:body><page:p>A</page:p><page:separator page:class="moin-hr6"/></page:body></page:page>',
            "A\n---------\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_separator(self, input, output):
        self.do(input, output)


coverage_modules = ["moin.converters.moinwiki_out"]
