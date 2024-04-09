# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.moinwiki_in
"""


import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import moin_page, xlink, html, xinclude

from moin.converters.moinwiki_in import Converter
from moin.converters._args import Arguments


class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", html: "xhtml", xinclude: "xinclude"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ("Text", "<page><body><p>Text</p></body></page>"),
        ("Text\nTest", "<page><body><p>Text\nTest</p></body></page>"),
        ("Text\n\nTest", "<page><body><p>Text</p><p>Test</p></body></page>"),
        (
            "[[http://moinmo.in/]]",
            '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>',
        ),
        (
            '[[javascript:alert("xss")]]',
            '<page><body><p><a xlink:href="wiki.local:javascript:alert%28%22xss%22%29">javascript:alert("xss")</a></p></body></page>',
        ),
        (
            "[[http://moinmo.in/|MoinMoin]]",
            '<page><body><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></body></page>',
        ),
        ("[[MoinMoin]]", '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
        (
            "[[MoinMoin#Heading]]",
            '<page><body><p><a xlink:href="wiki.local:MoinMoin#Heading">MoinMoin</a></p></body></page>',
        ),
        ("[[#Heading]]", '<page><body><p><a xlink:href="wiki.local:#Heading"></a></p></body></page>'),
        (
            "[[/inner2.png|{{/inner2.png||width=500}}]]",
            '<page><body><p><a xlink:href="wiki.local:/inner2.png"><xinclude:include xhtml:width="500" xinclude:href="wiki.local:/inner2.png?" /></a></p></body></page>',
        ),
        (
            "{{somelocalimage|my alt text|width=10, height=10}}",
            '<page><body><p><xinclude:include xhtml:alt="my alt text" xhtml:height="10" xhtml:width="10" xinclude:href="wiki.local:somelocalimage?" /></p></body></page>',
        ),
        # html5 requires img tags to have an alt attribute, html_out.py will add any required attributes that are missing
        (
            "{{somelocalimage||width=10, height=10}}",
            '<page><body><p><xinclude:include xhtml:height="10" xhtml:width="10" xinclude:href="wiki.local:somelocalimage?" /></p></body></page>',
        ),
        (
            "{{somelocalimage||width=10, &h=10}}",
            '<page><body><p><xinclude:include xhtml:width="10" xinclude:href="wiki.local:somelocalimage?h=10" /></p></body></page>',
        ),
        (
            "before {{somelocalimage}} middle {{somelocalimage}} after",
            '<page><body><p>before <xinclude:include xinclude:href="wiki.local:somelocalimage?" /> middle <xinclude:include xinclude:href="wiki.local:somelocalimage?" /> after</p></body></page>',
        ),
        (
            "before {{http://moinmo.in}} middle {{http://moinmo.in}} after",
            '<page><body><p>before <object xlink:href="http://moinmo.in" /> middle <object xlink:href="http://moinmo.in" /> after</p></body></page>',
        ),
        # in html5, object tags must not have alt attributes, html_out.py will adjust this so alt text is placed before the </object>
        (
            "{{http://moinmo.in/|test|width=10, height=10}}",
            '<page><body><p><object xhtml:alt="test" xhtml:height="10" xhtml:width="10" xlink:href="http://moinmo.in/" /></p></body></page>',
        ),
        ("{{http://moinmo.in/}}", '<page><body><p><object xlink:href="http://moinmo.in/" /></p></body></page>'),
        (
            "{{http://moinmo.in/|MoinMoin}}",
            '<page><body><p><object xhtml:alt="MoinMoin" xlink:href="http://moinmo.in/" /></p></body></page>',
        ),
        ("----", '<page><body><separator class="moin-hr1" /></body></page>'),
    ]

    @pytest.mark.parametrize("args", data)
    def test_base(self, args):
        self.do(*args)

    data = [
        (
            "Text",
            '<page><body style="background-color: red"><p>Text</p></body></page>',
            {"arguments": Arguments(keyword={"style": "background-color: red"})},
        )
    ]

    @pytest.mark.parametrize("input,output,args", data)
    def test_args(self, input, output, args):
        self.do(input, output, args)

    data = [
        ("''Emphasis''", "<page><body><p><emphasis>Emphasis</emphasis></p></body></page>"),
        ("'''Strong'''", "<page><body><p><strong>Strong</strong></p></body></page>"),
        ("'''''Both'''''", "<page><body><p><strong><emphasis>Both</emphasis></strong></p></body></page>"),
        (
            "'''''Mixed'''Emphasis''",
            "<page><body><p><emphasis><strong>Mixed</strong>Emphasis</emphasis></p></body></page>",
        ),
        ("'''''Mixed''Strong'''", "<page><body><p><strong><emphasis>Mixed</emphasis>Strong</strong></p></body></page>"),
        ("Text ''Emphasis\n''Text", "<page><body><p>Text <emphasis>Emphasis\n</emphasis>Text</p></body></page>"),
        ("Text ''Emphasis\n\nText", "<page><body><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></body></page>"),
        ("Text''''''Text''''", "<page><body><p>TextText</p></body></page>"),
        (
            "''italic '''strongitalic ''''' normal",
            "<page><body><p><emphasis>italic <strong>strongitalic </strong></emphasis> normal</p></body></page>",
        ),
        (
            "'''strong '''''italic '''strongitalic''''' normal",
            "<page><body><p><strong>strong </strong><emphasis>italic <strong>strongitalic</strong></emphasis> normal</p></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_emphasis(self, input, output):
        self.do(input, output)

    data = [
        (
            "=Not_a_Heading=",  # this is for better moin 1.x compatibility
            "<page><body><p>=Not_a_Heading=</p></body></page>",
        ),
        ("= Heading 1 =", '<page><body><h outline-level="1">Heading 1</h></body></page>'),
        ("== Heading 2 ==", '<page><body><h outline-level="2">Heading 2</h></body></page>'),
        ("=== Heading 3 ===", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ("==== Heading 4 ====", '<page><body><h outline-level="4">Heading 4</h></body></page>'),
        ("===== Heading 5 =====", '<page><body><h outline-level="5">Heading 5</h></body></page>'),
        ("====== Heading 6 ======", '<page><body><h outline-level="6">Heading 6</h></body></page>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_heading(self, input, output):
        self.do(input, output)

    data = [
        ("__underline__", "<page><body><p><ins>underline</ins></p></body></page>"),
        (",,sub,,script", '<page><body><p><span baseline-shift="sub">sub</span>script</p></body></page>'),
        ("^super^script", '<page><body><p><span baseline-shift="super">super</span>script</p></body></page>'),
        ("~-smaller-~", '<page><body><p><span font-size="85%">smaller</span></p></body></page>'),
        ("~+larger+~", '<page><body><p><span font-size="120%">larger</span></p></body></page>'),
        ("--(strike through)--", "<page><body><p><del>strike through</del></p></body></page>"),
        (
            "normal ~+big __underline__ big+~ normal",
            '<page><body><p>normal <span font-size="120%">big <ins>underline</ins> big</span> normal</p></body></page>',
        ),
        (
            "/* normal __underline__ normal */",
            '<page><body><p><span class="comment">normal <ins>underline</ins> normal</span></p></body></page>',
        ),
        ("&quot;", '<page><body><p>"</p></body></page>'),
        ("&#34;", '<page><body><p>"</p></body></page>'),
        ("&#x22;", '<page><body><p>"</p></body></page>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_inline(self, input, output):
        self.do(input, output)

    data = [
        (
            " *Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            " * Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            " 1. Item",
            '<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            " Key:: Item",
            "<page><body><list><list-item><list-item-label>Key</list-item-label><list-item-body>Item</list-item-body></list-item></list></body></page>",
        ),
        (
            "  Item",
            '<page><body><list item-label-generate="unordered" list-style-type="no-bullet"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            " *Item\nText",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>',
        ),
        (
            " *Item\n Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></body></page>',
        ),
        (
            " *Item 1\n *Item 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
        ),
        (
            " *Item 1\n  *Item 1.2\n *Item 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
        ),
        (
            " *List 1\n\n *List 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>',
        ),
        (
            " * List 1\n 1. List 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="ordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        ("<<BR>>", "<page><body /></page>"),
        ("Text<<BR>>Text", "<page><body><p>Text<line-break />Text</p></body></page>"),
        (
            "<<Macro>>",
            '<page><body><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>',
        ),
        (
            "<<Macro>><<Macro>>",
            '<page><body><p><inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /><inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>',
        ),
        (
            "<<Macro(arg)>>",
            '<page><body><part alt="&lt;&lt;Macro(arg)&gt;&gt;" content-type="x-moin/macro;name=Macro"><arguments>arg</arguments></part></body></page>',
        ),
        # these macro tests copied from test_creole_in, next test is different because leading space creates unordered list in moin2
        (
            " <<Macro>> ",
            '<page><body><list item-label-generate="unordered" list-style-type="no-bullet"><list-item><list-item-body><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></list-item-body></list-item></list></body></page>',
        ),
        (
            "Text <<Macro>>",
            '<page><body><p>Text <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>',
        ),
        (
            "Text <<Macro(arg)>>",
            '<page><body><p>Text <inline-part alt="&lt;&lt;Macro(arg)&gt;&gt;" content-type="x-moin/macro;name=Macro"><arguments>arg</arguments></inline-part></p></body></page>',
        ),
        (
            "Text\n<<Macro>>",
            '<page><body><p>Text</p><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>',
        ),
        (
            "Text\nText <<Macro>>",
            '<page><body><p>Text\nText <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>',
        ),
        (
            "Text\n\n<<Macro>>",
            '<page><body><p>Text</p><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_macro(self, input, output):
        self.do(input, output)

    data = [
        (
            "||Cell||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||Cell 1||Cell 2||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||Row 1||\n||Row 2||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||Cell 1.1||Cell 1.2||\n||Cell 2.1||Cell 2.2||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||Header||\n===\n||Body||\n=====\n||Footer||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell>Header</table-cell></table-row></table-body><table-body><table-row><table-cell>Body</table-cell></table-row></table-body><table-body><table-row><table-cell>Footer</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<<DateTime>>||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><inline-part alt="&lt;&lt;DateTime&gt;&gt;" content-type="x-moin/macro;name=DateTime" /></table-cell></table-row></table-body></table></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            "||{{cat}}||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><xinclude:include xinclude:href="wiki.local:cat?" /></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||{{cat|kitty}}||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><xinclude:include xhtml:alt="kitty" xinclude:href="wiki.local:cat?" /></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||{{cat|kitty|width=160}}||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><xinclude:include xhtml:alt="kitty" xhtml:width="160" xinclude:href="wiki.local:cat?" /></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||{{cat||width=160}} text {{cat||width=160}} text [[link]]||",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><xinclude:include xhtml:width="160" xinclude:href="wiki.local:cat?" /> text <xinclude:include xhtml:width="160" xinclude:href="wiki.local:cat?" /> text <a xlink:href="wiki.local:link">link</a></table-cell></table-row></table-body></table></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table_links(self, input, output):
        self.do(input, output)

    data = [
        # a class of moin-wiki-table is added to all tables, html_out may create thead and tfoot tags
        (
            "||||Span||\n\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell number-columns-spanned="2">Span</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<-2>Span||\n\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell number-columns-spanned="2">Span</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<|2>Span||\n\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell number-rows-spanned="2">Span</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<tableclass="table" rowclass="row" class="cell">Cell||\n',
            '<page><body><table class="table moin-wiki-table"><table-body><table-row class="row"><table-cell class="cell">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<tablestyle="table" rowstyle="row" style="cell">Cell||\n',
            '<page><body><table class="moin-wiki-table" style="table;"><table-body><table-row style="row;"><table-cell style="cell;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<tablestyle="background-color: yellow" rowstyle="background-color: red" #0000FF>Cell||\n',
            '<page><body><table class="moin-wiki-table" style="background-color: yellow;"><table-body><table-row style="background-color: red;"><table-cell style="background-color: #0000FF;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<width="20em">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="width: 20em;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<tablebgcolor="red">Cell||\n',
            '<page><body><table class="moin-wiki-table" style="background-color: red;"><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<rowbgcolor="red">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row style="background-color: red;"><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<bgcolor="red">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="background-color: red;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<tableid="my-id">Cell||\n',
            '<page><body><table class="moin-wiki-table" id="my-id"><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<rowid="my-id">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row id="my-id"><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<id="my-id">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell id="my-id">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<rowspan="2">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<colspan="2">Cell||\n',
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            '||<caption="My Table">Cell||\n',
            '<page><body><table class="moin-wiki-table"><caption>My Table</caption><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||'''Cell'''||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell><strong>Cell</strong></table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<^>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="vertical-align: top;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<v>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="vertical-align: bottom;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<(>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="text-align: left;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<:>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="text-align: center;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<)>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="text-align: right;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<99%>Cell||\n",
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="width: 99%;">Cell</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "||<X>Cell||\n",
            # '\xa0' below is equal to &nbsp;
            '<page><body><table class="moin-wiki-table"><table-body><table-row><table-cell style="background-color: pink; color: black;">[ Error: "X" is invalid within &lt;X&gt;'
            + "\xa0"
            + "]<line-break />Cell</table-cell></table-row></table-body></table></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table_attributes(self, input, output):
        self.do(input, output)

    data = [
        ("{{{nowiki}}}", "<page><body><p><samp>nowiki</samp></p></body></page>"),
        ("`nowiki`", "<page><body><p><code>nowiki</code></p></body></page>"),
        ("{{{{nowiki}}}}", "<page><body><p><samp>{nowiki}</samp></p></body></page>"),
        ("text: {{{nowiki}}}, text", "<page><body><p>text: <samp>nowiki</samp>, text</p></body></page>"),
        ("{{{\nnowiki\n}}}", "<page><body><nowiki>3<nowiki-args></nowiki-args>nowiki</nowiki></body></page>"),
        (
            "{{{\nnowiki\nno\nwiki\n}}}",
            "<page><body><nowiki>3<nowiki-args></nowiki-args>nowiki\nno\nwiki</nowiki></body></page>",
        ),
        ("{{{nowiki}}} {{{nowiki}}}", "<page><body><p><samp>nowiki</samp> <samp>nowiki</samp></p></body></page>"),
        ("{{{}}}", "<page><body><p><samp></samp></p></body></page>"),
        ("``", "<page><body><p><code></code></p></body></page>"),
        # XXX: Is <page> correct?
        ("{{{#!\ntest\n}}}", "<page><body><nowiki>3<nowiki-args>#!</nowiki-args>test</nowiki></body></page>"),
        (
            '{{{#!(style="background-color: red")\nwiki\n}}}',
            '<page><body><nowiki>3<nowiki-args>#!(style="background-color: red")</nowiki-args>wiki</nowiki></body></page>',
        ),
        (
            "{{{#!text/plain\ntext\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!text/plain</nowiki-args>text</nowiki></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_nowiki(self, input, output):
        self.do(input, output)

    data = [
        ("{{{#!wiki\nwiki\n}}}", "<page><body><nowiki>3<nowiki-args>#!wiki</nowiki-args>wiki</nowiki></body></page>"),
        (
            "{{{{{#!wiki\nwiki\n}}}}}",
            "<page><body><nowiki>5<nowiki-args>#!wiki</nowiki-args>wiki</nowiki></body></page>",
        ),
        (
            '{{{#!wiki(style="background-color: red")\nwiki\n}}}',
            '<page><body><nowiki>3<nowiki-args>#!wiki(style="background-color: red")</nowiki-args>wiki</nowiki></body></page>',
        ),
        (
            "{{{#!highlight python\nimport os\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!highlight python</nowiki-args>import os</nowiki></body></page>",
        ),
        (
            "{{{#!python\nimport os\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!python</nowiki-args>import os</nowiki></body></page>",
        ),
        (
            "{{{#!csv\na;b;c\nd;e;22\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!csv</nowiki-args>a;b;c\nd;e;22</nowiki></body></page>",
        ),
        (
            "{{{#!csv ,\na,b,c\nd,e,22\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!csv ,</nowiki-args>a,b,c\nd,e,22</nowiki></body></page>",
        ),
        # TODO: Backward compatibility
        (
            "{{{#!wiki red/solid\nwiki\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!wiki red/solid</nowiki-args>wiki</nowiki></body></page>",
        ),
        (
            "{{{#!wiki red/solid\nwiki\n\nwiki\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!wiki red/solid</nowiki-args>wiki\n\nwiki</nowiki></body></page>",
        ),
        (
            "{{{#!rst\nHeading\n-------\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!rst</nowiki-args>Heading\n-------</nowiki></body></page>",
        ),
        (
            "{{{#!docbook\n<article xmlns='http://docbook.org/ns/docbook' xmlns:xlink='http://www.w3.org/1999/xlink'>\n<section>\n<title>A docbook document</title>\n</section>\n</article>\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!docbook</nowiki-args>&lt;article xmlns='http://docbook.org/ns/docbook' xmlns:xlink='http://www.w3.org/1999/xlink'&gt;\n&lt;section&gt;\n&lt;title&gt;A docbook document&lt;/title&gt;\n&lt;/section&gt;\n&lt;/article&gt;</nowiki></body></page>",
        ),
        (
            "{{{#!creole\n|=A|1\n|=B|2\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!creole</nowiki-args>|=A|1\n|=B|2</nowiki></body></page>",
        ),
        (
            "{{{#!text/x.moin.creole\ntext\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!text/x.moin.creole</nowiki-args>text</nowiki></body></page>",
        ),
        (
            "{{{#!markdown\n~~~\naaa\nbbb\nccc\n~~~\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!markdown</nowiki-args>~~~\naaa\nbbb\nccc\n~~~</nowiki></body></page>",
        ),
        (
            "{{{#!mediawiki\n=== Level 3 ===\n}}}",
            "<page><body><nowiki>3<nowiki-args>#!mediawiki</nowiki-args>=== Level 3 ===</nowiki></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_nowiki_parsers(self, input, output):
        self.do(input, output)

    data = [
        (
            "Text\n * Item\n\nText",
            '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>',
        ),
        (
            "Text\n||Item||\nText",
            '<page><body><p>Text</p><table class="moin-wiki-table"><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_composite(self, input, output):
        self.do(input, output)

    data = [
        (
            "[[MoinMoin:RecentChanges]]",
            '<page><body><p><a xlink:href="wiki://MoinMoin/RecentChanges">RecentChanges</a></p></body></page>',
        ),
        (
            "[[MoinMoin:RecentChanges|changes]]",
            '<page><body><p><a xlink:href="wiki://MoinMoin/RecentChanges">changes</a></p></body></page>',
        ),
        (
            "[[MoinMoin:Foo/Bar.Baz]]",
            '<page><body><p><a xlink:href="wiki://MoinMoin/Foo/Bar.Baz">Foo/Bar.Baz</a></p></body></page>',
        ),
        (
            "[[MoinMoin:Blank In Page Name|blank in page name]]",
            '<page><body><p><a xlink:href="wiki://MoinMoin/Blank%20In%20Page%20Name">blank in page name</a></p></body></page>',
        ),
        (
            "[[InvalidWikiName:RecentChanges]]",
            '<page><body><p><a xlink:href="wiki.local:InvalidWikiName:RecentChanges">InvalidWikiName:RecentChanges</a></p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_interwiki(self, input, output):
        self.do(input, output)

    data = [
        ("[[mailto:root]]", '<page><body><p><a xlink:href="mailto:root">mailto:root</a></p></body></page>'),
        (
            "[[mailto:foo@bar.baz]]",
            '<page><body><p><a xlink:href="mailto:foo@bar.baz">mailto:foo@bar.baz</a></p></body></page>',
        ),
        (
            "[[mailto:foo@bar.baz|write me]]",
            '<page><body><p><a xlink:href="mailto:foo@bar.baz">write me</a></p></body></page>',
        ),
        (
            "[[mailto:foo.bar_baz@bar.baz]]",  # . and _ are special characters commonly allowed by email systems
            '<page><body><p><a xlink:href="mailto:foo.bar_baz@bar.baz">mailto:foo.bar_baz@bar.baz</a></p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_email(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv(input, "text/x.moin.wiki;charset=utf-8", **args)
        assert self.serialize_strip(out) == output
