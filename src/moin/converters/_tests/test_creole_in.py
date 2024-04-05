# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.creole_in
"""

import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import moin_page, xlink, html, xinclude
from moin.converters._args import Arguments

from ..creole_in import Converter


class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", html: "xhtml", xinclude: "xinclude"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ("Text", "<page><body><p>Text</p></body></page>"),
        ("Text\nTest", "<page><body><p>Text\nTest</p></body></page>"),
        ("Text\n\nTest", "<page><body><p>Text</p><p>Test</p></body></page>"),
        ("Line\\\\Break", "<page><body><p>Line<line-break />Break</p></body></page>"),
        ("Line\\\\\nBreak", "<page><body><p>Line<line-break />\nBreak</p></body></page>"),
        (
            "http://moinmo.in/",
            '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>',
        ),
        (
            "[[http://moinmo.in/]]",
            '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>',
        ),
        (
            "[[MoinMoin:InterWiki]]",
            '<page><body><p><a xlink:href="wiki://MoinMoin/InterWiki">InterWiki</a></p></body></page>',
        ),
        (
            "[[mailto:fred@flinstones.org|drop me a note]]",
            '<page><body><p><a xlink:href="mailto:fred@flinstones.org">drop me a note</a></p></body></page>',
        ),
        (
            "[[xmpp:room@conference.example.com?join|the chatroom]]",
            '<page><body><p><a xlink:href="xmpp:room@conference.example.com?join">the chatroom</a></p></body></page>',
        ),
        # garbage input defaults to wiki.local name
        (
            "[[invalid:fred@flinstones.org|drop me a note]]",
            '<page><body><p><a xlink:href="wiki.local:invalid:fred@flinstones.org">drop me a note</a></p></body></page>',
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
            "{{http://moinmo.in/}}",
            '<page><body><p><object xlink:href="http://moinmo.in/">Your Browser does not support HTML5 audio/video element.</object></p></body></page>',
        ),
        (
            "{{http://moinmo.in/|MoinMoin}}",
            '<page><body><p><object xhtml:alt="MoinMoin" xlink:href="http://moinmo.in/">Your Browser does not support HTML5 audio/video element.</object></p></body></page>',
        ),
        ("{{my.png}}", '<page><body><p><xinclude:include xinclude:href="wiki.local:my.png" /></p></body></page>'),
        ("----", '<page><body><separator class="moin-hr3" /></body></page>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            "Text",
            '<page><body style="background-color: red"><p>Text</p></body></page>',
            {"arguments": Arguments(keyword={"style": "background-color: red"})},
        )
    ]

    @pytest.mark.parametrize("args", data)
    def test_args(self, args):
        self.do(*args)

    data = [
        ("//Emphasis//", "<page><body><p><emphasis>Emphasis</emphasis></p></body></page>"),
        ("**Strong**", "<page><body><p><strong>Strong</strong></p></body></page>"),
        ("//**Both**//", "<page><body><p><emphasis><strong>Both</strong></emphasis></p></body></page>"),
        ("**//Both//**", "<page><body><p><strong><emphasis>Both</emphasis></strong></p></body></page>"),
        ("Text //Emphasis\n//Text", "<page><body><p>Text <emphasis>Emphasis\n</emphasis>Text</p></body></page>"),
        ("Text //Emphasis\n\nText", "<page><body><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></body></page>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_emphasis(self, input, output):
        self.do(input, output)

    data = [
        ("~http://moinmo.in/", "<page><body><p>http://moinmo.in/</p></body></page>"),
        ("~[[escape]]", "<page><body><p>[[escape]]</p></body></page>"),
        ("~<<escape>>", "<page><body><p>&lt;&lt;escape&gt;&gt;</p></body></page>"),
        ("~{~{{escape}}}", "<page><body><p>{{{escape}}}</p></body></page>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_escape(self, input, output):
        self.do(input, output)

    data = [
        ("= Heading 1", '<page><body><h outline-level="1">Heading 1</h></body></page>'),
        ("== Heading 2", '<page><body><h outline-level="2">Heading 2</h></body></page>'),
        ("=== Heading 3", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ("==== Heading 4", '<page><body><h outline-level="4">Heading 4</h></body></page>'),
        ("===== Heading 5", '<page><body><h outline-level="5">Heading 5</h></body></page>'),
        ("====== Heading 6", '<page><body><h outline-level="6">Heading 6</h></body></page>'),
        ("= Heading 1 =", '<page><body><h outline-level="1">Heading 1</h></body></page>'),
        ("== Heading 2 ==", '<page><body><h outline-level="2">Heading 2</h></body></page>'),
        ("=== Heading 3 ===", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ("==== Heading 4 ====", '<page><body><h outline-level="4">Heading 4</h></body></page>'),
        ("===== Heading 5 =====", '<page><body><h outline-level="5">Heading 5</h></body></page>'),
        ("====== Heading 6 ======", '<page><body><h outline-level="6">Heading 6</h></body></page>'),
        ("=== Heading 3", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ("=== Heading 3 =", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ("=== Heading 3 ==", '<page><body><h outline-level="3">Heading 3</h></body></page>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_heading(self, input, output):
        self.do(input, output)

    data = [
        (
            "* Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            " *Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            "*Item",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            "* Item\nItem",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></body></page>',
        ),
        (
            "* Item 1\n*Item 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
        ),
        (
            "* Item 1\n** Item 1.2\n* Item 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
        ),
        (
            "* List 1\n\n* List 2",
            '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>',
        ),
        (
            "# Item",
            '<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
        ),
        (
            "* List 1\n# List 2",
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
        (
            " <<Macro>> ",
            '<page><body><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>',
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
            "|Cell",
            "<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|    Cell     ",
            "<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|Cell|",
            "<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|=Heading|",
            '<page><body><table><table-body><table-row><table-cell class="moin-thead">Heading</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "|Cell 1|Cell 2",
            "<page><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|Cell 1|Cell 2|",
            "<page><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|Row 1\n|Row 2\n",
            "<page><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|Row 1|\n|Row 2|\n",
            "<page><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>",
        ),
        (
            "|Cell 1.1|Cell 1.2|\n|Cell 2.1|Cell 2.2|\n",
            "<page><body><table><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></body></page>",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        ("{{{nowiki}}}", "<page><body><p><code>nowiki</code></p></body></page>"),
        ("{{{{nowiki}}}}", "<page><body><p><code>{nowiki}</code></p></body></page>"),
        ("text: {{{nowiki}}}, text", "<page><body><p>text: <code>nowiki</code>, text</p></body></page>"),
        ("{{{\nnowiki\n}}}", "<page><body><blockcode>nowiki</blockcode></body></page>"),
        ("{{{\nnowiki\nno\nwiki\n}}}", "<page><body><blockcode>nowiki\nno\nwiki</blockcode></body></page>"),
        ("{{{nowiki}}} {{{nowiki}}}", "<page><body><p><code>nowiki</code> <code>nowiki</code></p></body></page>"),
        # XXX: Is <page> correct?
        ("{{{\n#!\nwiki\n}}}", "<page><body><page><body><p>wiki</p></body></page></body></page>"),
        (
            '{{{\n#!(style="background-color: red")\nwiki\n}}}',
            '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>',
        ),
        ("{{{\n#!creole\nwiki\n}}}", "<page><body><page><body><p>wiki</p></body></page></body></page>"),
        (
            '{{{\n#!creole(style="background-color: red")\nwiki\n}}}',
            '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>',
        ),
        (
            "{{{\n#!text/plain\ntext\n}}}",
            '<page><body><part content-type="text/plain"><body>text</body></part></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_nowiki(self, input, output):
        self.do(input, output)

    data = [
        (
            "Text\n* Item\n\nText",
            '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>',
        ),
        (
            "Text\n* Item\n= Heading",
            '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><h outline-level="1">Heading</h></body></page>',
        ),
        (
            "Text\n* Item\n{{{\nnowiki\n}}}",
            '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><blockcode>nowiki</blockcode></body></page>',
        ),
        (
            "Text\n* Item\n|Item",
            '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table></body></page>',
        ),
        (
            "Text\n|Item\nText",
            "<page><body><p>Text</p><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></body></page>",
        ),
        (
            "| text [[http://localhost | link]] |",
            '<page><body><table><table-body><table-row><table-cell>text <a xlink:href="http://localhost">link</a></table-cell></table-row></table-body></table></body></page>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_composite(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}):
        out = self.conv(input, "text/x.moin.creole;charset=utf-8", **args)
        assert self.serialize_strip(out) == output
