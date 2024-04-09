# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.markdown_in
"""

import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import moin_page, xlink, xinclude, html

from ..markdown_in import Converter


class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", xinclude: "xinclude", html: "html"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ("Text", "<p>Text</p>"),
        ("Text\nTest", "<p>Text\nTest</p>"),
        ("Text\n\nTest", "<p>Text</p><p>Test</p>"),
        ("<http://moinmo.in/>", '<p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p>'),
        (
            '[yo](javascript:alert("xss"))',
            '<p><a title="xss" html:title="xss" xlink:href="javascript:alert%28">yo</a>)</p>',
        ),
        ("[MoinMoin](http://moinmo.in/)", '<p><a xlink:href="http://moinmo.in/">MoinMoin</a></p>'),
        ("----", '<separator class="moin-hr3" />'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        ("*Emphasis*", "<p><emphasis>Emphasis</emphasis></p>"),
        ("_Emphasis_", "<p><emphasis>Emphasis</emphasis></p>"),
        ("**Strong**", "<p><strong>Strong</strong></p>"),
        ("_**Both**_", "<p><emphasis><strong>Both</strong></emphasis></p>"),
        ("**_Both_**", "<p><strong><emphasis>Both</emphasis></strong></p>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_emphasis(self, input, output):
        self.do(input, output)

    data = [
        ("<em>Emphasis</em>", "<div><p><emphasis>Emphasis</emphasis></p></div>"),
        ("<i>Italic</i>", "<div><p><emphasis>Italic</emphasis></p></div>"),
        ("<u>underline</u>", "<div><p><u>underline</u></p></div>"),
        ("<del>deleted</del>", "<div><p><del>deleted</del></p></div>"),
        # TODO: markdown 3.3 outputs `/>\n\n\n\n</p>`, prior versions output `/></p>`. Try test again with versions 3.3+
        # Added similar test to test_markdown_in_out
        # ('<hr>',
        #  '<div><p><separator html:class="moin-hr3" />\n\n\n\n</p></div>'),  # works only with markdown 3.3
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_html_extension(self, input, output):
        self.do(input, output)

    data = [
        ("http://moinmo.in/", "<p>http://moinmo.in/</p>"),
        ("\\[escape](yo)", "<p>[escape](yo)</p>"),
        ("\\*yo\\*", "<p>*yo*</p>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_escape(self, input, output):
        self.do(input, output)

    data = [
        (
            "* Item",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list>',
        ),
        (
            "* Item\nItem",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list>',
        ),
        (
            "* Item 1\n* Item 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>',
        ),
        (
            "* Item 1\n    * Item 1.2\n* Item 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>',
        ),
        (
            "* List 1\n\nyo\n\n\n* List 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><p>yo</p><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list>',
        ),
        (
            "8. Item",
            '<list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            '![Alt text](png "Optional title")',
            '<p><xinclude:include html:alt="Alt text" html:title="Optional title" xinclude:href="wiki.local:png" /></p>',
        ),
        (
            '![](png "Optional title")',
            '<p><xinclude:include html:title="Optional title" xinclude:href="wiki.local:png" /></p>',
        ),
        (
            "![remote image](http://static.moinmo.in/logos/moinmoin.png)",
            '<p><object html:alt="remote image" xlink:href="http://static.moinmo.in/logos/moinmoin.png" /></p>',
        ),
        (
            "![Alt text](http://test.moinmo.in/png)",
            '<p><object html:alt="Alt text" xlink:href="http://test.moinmo.in/png" /></p>',
        ),
        (
            "![transclude local wiki item](someitem)",
            '<p><xinclude:include html:alt="transclude local wiki item" xinclude:href="wiki.local:someitem" /></p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_image(self, input, output):
        self.do(input, output)

    data = [
        (
            "First Header  | Second Header\n------------- | -------------\nContent Cell  | Content Cell\nContent Cell  | Content Cell",
            "<table><table-header><table-row><table-cell-head>First Header</table-cell-head><table-cell-head>Second Header</table-cell-head></table-row></table-header><table-body><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row></table-body></table>",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        ("[[Bracketed]]", '<p><a xlink:href="wiki.local:Bracketed">Bracketed</a></p>'),
        (
            "[[Main/sub]]",  # check if label is kept lower case, check if slash in link is detected
            '<p><a xlink:href="wiki.local:Main/sub">sub</a></p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_wikilinks(self, input, output):
        """Test the Wikilinks extension: https://python-markdown.github.io/extensions/wikilinks/"""
        self.do(input, output)

    data = [
        (
            "!!! note\n    You should note that the title will be automatically capitalized.",
            '<div class="admonition note"><p class="admonition-title">Note</p><p>You should note that the title will be automatically capitalized.</p></div>',
        ),
        (
            '!!! danger "Don\'t try this at home"\n    ...',
            '<div class="admonition danger"><p class="admonition-title">Don\'t try this at home</p><p>...</p></div>',
        ),
        (
            '!!! important ""\n    This is an admonition box without a title.',
            '<div class="admonition important"><p>This is an admonition box without a title.</p></div>',
        ),
        (
            '!!! danger highlight blink "Don\'t try this at home"\n    ...',
            '<div class="admonition danger highlight blink"><p class="admonition-title">Don\'t try this at home</p><p>...</p></div>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_admonition(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}):
        out = self.conv(input, "text/x-markdown;charset=utf-8", **args)
        got_output = self.serialize_strip(out)
        desired_output = "<page><body>%s</body></page>" % output
        print("------------------------------------")
        print("WANTED:")
        print(desired_output)
        print("GOT:")
        print(got_output)
        assert got_output == desired_output
