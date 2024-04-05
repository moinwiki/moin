# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.mediawiki_in
"""

import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import moin_page, xlink
from moin.converters.mediawiki_in import Converter


class TestConverter:
    namespaces = {moin_page.namespace: "", xlink.namespace: "xlink"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ("''italic''", "<page><body><p><emphasis>italic</emphasis></p></body></page>"),
        ("Text\nTest", "<page><body><p>Text\nTest</p></body></page>"),
        ("Text\n\nTest", "<page><body><p>Text</p><p>Test</p></body></page>"),
        ("'''bold'''", "<page><body><p><strong>bold</strong></p></body></page>"),
        (
            "'''''bold and italic'''''",
            "<page><body><p><strong><emphasis>bold and italic</emphasis></strong></p></body></page>",
        ),
        (
            "<nowiki>no ''markup''</nowiki>\n\n<code>no ''markup''</code>\n\n<tt>no ''markup''</tt>",
            "<page><body><p><code>no ''markup''</code></p><p><code>no ''markup''</code></p><p><code>no ''markup''</code></p></body></page>",
        ),
        (
            "<pre>no ''markup'' block</pre>",
            "<page><body><p><blockcode>no ''markup'' block</blockcode></p></body></page>",
        ),
        ("<u>underlined</u>", "<page><body><p><u>underlined</u></p></body></page>"),
        ("<ins>inserted</ins>", "<page><body><p><ins>inserted</ins></p></body></page>"),
        ("<del>Strikethrough</del>", "<page><body><p><del>Strikethrough</del></p></body></page>"),
        ("<s>Strikethrough</s>", "<page><body><p><s>Strikethrough</s></p></body></page>"),
        (
            "test <sup>super</sup> or <sub>sub</sub>",
            '<page><body><p>test <span baseline-shift="super">super</span> or <span baseline-shift="sub">sub</span></p></body></page>',
        ),
        (
            "text <blockquote> quote quote quote quote quote quote </blockquote> text",
            "<page><body><p>text <blockquote> quote quote quote quote quote quote </blockquote> text</p></body></page>",
        ),
        ("aaa<br />bbb", "<page><body><p>aaa<line-break />bbb</p></body></page>"),
        (
            "aaa <ref> sdf </ref> test\n\n asd",
            '<page><body><p>aaa <note note-class="footnote"><note-body> sdf </note-body></note> test</p><p> asd</p></body></page>',
        ),
        (
            """=level 1=
== level 2 ==
===level 3===
====level 4====
=====level 5=====
======level 6======
""",
            '<page><body><h outline-level="1">level 1</h><h outline-level="2">level 2</h><h outline-level="3">level 3</h><h outline-level="4">level 4</h><h outline-level="5">level 5</h><h outline-level="6">level 6</h></body></page>',
        ),
        ("[javascript:alert('xss')]", "<page><body><p>[javascript:alert('xss')]</p></body></page>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            """* one
* two
* three
** three point one
** three point two
""",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two</p></list-item-body></list-item><list-item><list-item-body><p>three</p><list item-label-generate="unordered"><list-item><list-item-body><p>three point one</p></list-item-body></list-item><list-item><list-item-body><p>three point two</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>',
        ),
        (
            """# one
# two<br />spanning more lines<br />doesn't break numbering
# three
## three point one
## three point two
# 4
no point
""",
            """<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two<line-break />spanning more lines<line-break />doesn't break numbering</p></list-item-body></list-item><list-item><list-item-body><p>three</p><list item-label-generate="ordered"><list-item><list-item-body><p>three point one</p></list-item-body></list-item><list-item><list-item-body><p>three point two</p></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>4</p></list-item-body></list-item></list><p>no point</p></body></page>""",
        ),
        (
            """;item 1:definition 1
;item 2:definition 2
""",
            """\
<page><body>\
<list>\
<list-item>\
<list-item-label>item 1</list-item-label>\
<list-item-body><p>definition 1</p></list-item-body>\
</list-item>\
<list-item>\
<list-item-label>item 2</list-item-label>\
<list-item-body><p>definition 2</p></list-item-body>\
</list-item>\
</list>\
</body></page>\
""",
        ),
        # TODO add a test for a definition list with term and definition on separate lines like:
        # ; term
        # : definition
        (
            ";aaa : bbb",
            "<page><body><list><list-item><list-item-label>aaa </list-item-label><list-item-body><p> bbb</p></list-item-body></list-item></list></body></page>",
        ),
        (
            """: Single indent
:: Double indent
::::: Multiple indent
""",
            '<page><body><list item-label-generate="None"><list-item><list-item-body><p>Single indent</p><list item-label-generate="None"><list-item><list-item-body><p>Double indent</p><list item-label-generate="None"><list-item><list-item-body><p>Multiple indent</p></list-item-body></list-item></list></list-item-body></list-item></list></list-item-body></list-item></list></body></page>',
        ),
        (
            """# one
# two
#* two point one
#* two point two
# three
#; three item one:three def one
""",
            '<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two</p><list item-label-generate="unordered"><list-item><list-item-body><p>two point one</p></list-item-body></list-item><list-item><list-item-body><p>two point two</p></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>three</p><list><list-item><list-item-label>three item one</list-item-label><list-item-body><p>three def one</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            """{|
|Orange
|Apple
|-
|Bread
|Pie
|-
|Butter
|Ice cream
|}
""",
            "<page><body><table><table-body><table-row><table-cell>Orange</table-cell><table-cell>Apple</table-cell></table-row><table-row><table-cell>Bread</table-cell><table-cell>Pie</table-cell></table-row><table-row><table-cell>Butter</table-cell><table-cell>Ice cream</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            """{|style="border-width: 1px;"
|style="border-style: solid; border-width: 1px" colspan="2"| Orange
Apple
|-
|rowspan='2'| Bread
|Pie
|-
|test
|}
""",
            '<page><body><table style="border-width: 1px;"><table-body><table-row><table-cell number-columns-spanned="2" style="border-style: solid; border-width: 1px">Orange\nApple</table-cell></table-row><table-row><table-cell number-rows-spanned="2">Bread</table-cell><table-cell>Pie</table-cell></table-row><table-row><table-cell>test</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            """{|
|class="test"|text||style="border:1px"|test
|}
""",
            '<page><body><table><table-body><table-row><table-cell class="test">text</table-cell><table-cell style="border:1px">test</table-cell></table-row></table-body></table></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        ("[[SomeLink]]", '<page><body><p><a xlink:href="wiki.local:SomeLink">SomeLink</a></p></body></page>'),
        ("[http://external.link]", '<page><body><p><a xlink:href="http://external.link"></a></p></body></page>'),
        (
            "[http://external.link alt text]",
            '<page><body><p><a xlink:href="http://external.link">alt text</a></p></body></page>',
        ),
        (
            "[[SomeLink|Some text]]",
            '<page><body><p><a xlink:href="wiki.local:SomeLink">Some text</a></p></body></page>',
        ),
        (
            "[[SomeLink|arg1=value|arg2=otherval|Some text]]",
            '<page><body><p><a xlink:href="wiki.local:SomeLink?arg1=value&amp;arg2=otherval">Some text</a></p></body></page>',
        ),
        (
            "[[File:Test.jpg|test]]",
            '<page><body><p><object alt="test" xlink:href="wiki.local:Test.jpg?do=get">test</object></p></body></page>',
        ),
        (
            "[[File:MyImage.png]]",
            '<page><body><p><object alt="MyImage.png" xlink:href="wiki.local:MyImage.png?do=get">MyImage.png</object></p></body></page>',
        ),
        (
            "[[File:MyImage.png|arg=http://google.com|caption]]",
            '<page><body><p><object alt="caption" xlink:href="wiki.local:MyImage.png?arg=http%253A%252F%252Fgoogle.com&amp;do=get">caption</object></p></body></page>',
        ),
        (
            "[[File:Test.png|do=get|arg1=test|arg2=something else]]",
            '<page><body><p><object alt="Test.png" xlink:href="wiki.local:Test.png?do=get&amp;arg1=test&amp;arg2=something+else">Test.png</object></p></body></page>',
        ),
        # The do=xxx part is just to test if do in args is being updated correctly, it's invalid otherwise
        (
            "[[File:Test2.png|do=xxx|caption|arg1=test]]",
            '<page><body><p><object alt="caption" xlink:href="wiki.local:Test2.png?do=xxx&amp;arg1=test">caption</object></p></body></page>',
        ),
        (
            "[[File:myimg.png|'Graph showing width |= k for 5 < k < 10']]",
            '<page><body><p><object alt="Graph showing width |= k for 5 &lt; k &lt; 10" xlink:href="wiki.local:myimg.png?do=get">Graph showing width |= k for 5 &lt; k &lt; 10</object></p></body></page>',
        ),
        (
            "[[File:myimg.png|arg1='longish caption value with |= to test'|arg2=other|test stuff]]",
            '<page><body><p><object alt="test stuff" xlink:href="wiki.local:myimg.png?arg1=longish+caption+value+with+%257C%253D+to+test&amp;arg2=other&amp;do=get">test stuff</object></p></body></page>',
        ),
        # Unicode test
        (
            "[[File:Test.jpg|\xe8]]",
            '<page><body><p><object alt="\xe8" xlink:href="wiki.local:Test.jpg?do=get">\xe8</object></p></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_links(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input, "text/x-mediawiki;charset=utf-8", **args)
        result = self.serialize_strip(out)
        print(result)
        assert result == output


coverage_modules = ["moin.converters.mediawiki_in"]
