# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.converters.markdown_in tests.
"""

import pytest

from collections import namedtuple
from flask import Flask

from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.converters.markdown_in import Converter
from moin.i18n import i18n_init

from . import serialize, XMLNS_RE

DefaultConfig = namedtuple("DefaultConfig", ("markdown_extensions", "locale_default"))
config = DefaultConfig(markdown_extensions=[], locale_default="en")


@pytest.fixture
def _app_context_with_markdown_extensions_config():
    """
    A fixture providing an application context with just the Moin2 configuration
    settings required by the markdown_in converter.
    """
    app = Flask(__name__)
    app.cfg = config
    i18n_init(app)
    with app.app_context() as context:
        yield context


@pytest.mark.usefixtures("_app_context_with_markdown_extensions_config")
class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", xinclude: "xinclude", html: "html"}

    output_re = XMLNS_RE

    @pytest.mark.parametrize(
        "input,output",
        [
            ("Text", "<p>Text</p>"),
            ("Text\nTest", "<p>Text\nTest</p>"),
            ("Text\n\nTest", "<p>Text</p><p>Test</p>"),
            ("<http://moinmo.in/>", '<p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p>'),
            (  # ensure a safe scheme, fall back to wiki-internal reference:
                '[yo](javascript:alert("xss"))',
                '<p><a title="xss" html:title="xss" xlink:href="wiki.local:javascript:alert%28">yo</a>)</p>',
            ),
            (
                "[new page](Yesterday: a legacy)",
                '<p><a xlink:href="wiki.local:Yesterday:%20a%20legacy">new page</a></p>',
            ),
            ("[MoinMoin](http://moinmo.in/)", '<p><a xlink:href="http://moinmo.in/">MoinMoin</a></p>'),
            (  # & may be given as literal or entity
                "[query](http:example.org?num=20&amp;q=top&x=u)",
                '<p><a xlink:href="http:example.org?num=20&amp;q=top&amp;x=u">query</a></p>',
            ),
            ("----", '<separator class="moin-hr3" />'),
        ],
    )
    def test_base(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ("*Emphasis*", "<p><emphasis>Emphasis</emphasis></p>"),
            ("_Emphasis_", "<p><emphasis>Emphasis</emphasis></p>"),
            ("**Strong**", "<p><strong>Strong</strong></p>"),
            ("_**Both**_", "<p><emphasis><strong>Both</strong></emphasis></p>"),
            ("**_Both_**", "<p><strong><emphasis>Both</emphasis></strong></p>"),
        ],
    )
    def test_emphasis(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ("http://moinmo.in/", "<p>http://moinmo.in/</p>"),
            ("\\[escape](yo)", "<p>[escape](yo)</p>"),
            ("\\*yo\\*", "<p>*yo*</p>"),
        ],
    )
    def test_escape(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
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
        ],
    )
    def test_list(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
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
        ],
    )
    def test_image(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            (
                "First Header  | Second Header\n------------- | -------------\nContent Cell  | Content Cell\nContent Cell  | Content Cell",
                "<table><table-header><table-row><table-cell-head>First Header</table-cell-head><table-cell-head>Second Header</table-cell-head></table-row></table-header><table-body><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row></table-body></table>",
            )
        ],
    )
    def test_table(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            # TODO: spurious empty <span>
            (
                "```\nstart\nstop\n```",
                '<div><div html:class="codehilite"><blockcode><span /><code>start\nstop\n</code></blockcode></div>\n</div>',
            )
        ],
    )
    def test_code_block(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ("start `pre` end", "<p>start <code>pre</code> end</p>"),
            ("start `abc < def` end", "<p>start <code>abc &lt; def</code> end</p>"),
            ("start `abc &lt; def` end", "<p>start <code>abc &amp;lt; def</code> end</p>"),
            ("start `[TOC]` end", "<p>start <code>[TOC]</code> end</p>"),
            ("``start `code` end``", "<p><code>start `code` end</code></p>"),
        ],
    )
    def test_code(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ("< & >", "<p>&lt; &amp; &gt;</p>"),
            ("<strong>0 < 1</strong>", "<p><strong>0 &lt; 1</strong></p>"),
            ("<strong>0 &lt; 1</strong>", "<p><strong>0 &lt; 1</strong></p>"),
        ],
    )
    def test_character_entities(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ("[[Bracketed]]", '<p><a xlink:href="wiki.local:Bracketed">Bracketed</a></p>'),
            (
                "[[Main/sub]]",  # check if label is kept lower case, check if slash in link is detected
                '<p><a xlink:href="wiki.local:Main/sub">sub</a></p>',
            ),
            (  # TODO: do we want code highlight in simple pre-formatted blocks? Spurious empty <span>.
                '    "preformatted" code is rendered in a <pre> element.\n',
                '<div><div html:class="codehilite"><blockcode><span /><code>'
                '"preformatted" code is rendered in a &lt;pre&gt; element.\n'
                "</code></blockcode></div>\n"
                "</div>",
            ),
            (  # TODO: code language should become class value, spurious empty <span>
                "~~~ python\n" "def hello():\n" '    print "Hello World!"\n' "~~~\n",
                '<div><div html:class="codehilite"><blockcode><span /><code>'
                '<span html:class="k">def</span><span html:class="w"> </span>'
                '<span html:class="nf">hello</span><span html:class="p">():</span>\n'
                '    <span html:class="nb">print</span> <span html:class="s2">"Hello World!"</span>\n'
                "</code></blockcode></div>\n"
                "</div>",
            ),
        ],
    )
    def test_extensions(self, input, output):
        """Test Markdown extensions: https://python-markdown.github.io/extensions/"""
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
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
        ],
    )
    def test_admonition(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            # only complete/correct tags are recognized.
            ("one < two", "<p>one &lt; two</p>"),
            ("[[one]] < two", '<p><a xlink:href="wiki.local:one">one</a> &lt; two</p>'),
            ("pre <strong>bold</strong> post", "<p>pre <strong>bold</strong> post</p>"),
            # block-level elements
            # TODO: convert_invalid_p_nodes() keeps spurious <div>s.
            (
                "<address>webmaster@example.org</address>",
                '<div><div html-tag="address">webmaster@example.org</div>\n</div>',
            ),
            (  # TODO: invalid <p>
                "<ul><li><em>Item</em></li></ul>",
                '<p><list item-label-generate="unordered"><list-item><list-item-body><emphasis>Item</emphasis></list-item-body></list-item></list>\n</p>',
            ),
            (
                '<table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table>',
                '<div><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table>\n</div>',
            ),
            # Markdown markup in block-level HTML tags is not processed (https://daringfireball.net/projects/markdown/syntax#html)
            ("<p>**nice** <em>trick</em></p>", "<div><p>**nice** <emphasis>trick</emphasis></p>\n</div>"),
            ("<h2>**strong** heading</h2>", '<div><h outline-level="2">**strong** heading</h>\n</div>'),
            ('<pre>2*3*4\n print("s")</pre>', '<div><blockcode>2*3*4\n print("s")</blockcode>\n</div>'),
            ("<map><p>**nice**</p></map>", "<p>\n</p>"),
            # explicitly ignored tags (html_in.HtmlTags.ignored_tags) are dropped together with their content:
            ("<button>Stop</button>", "<p />"),
            ("<script>2*3*4</script>", "<p>\n</p>"),
            # TODO: markdown 3.3 outputs `/>\n\n\n\n</p>`, prior versions output `/></p>`. Try test again with versions 3.3+
            # Added similar test to test_markdown_in_out
            # ('<hr>',
            #  '<p><separator html:class="moin-hr3" />\n\n\n\n</p>'),  # works only with markdown 3.3
            # <hr> is a block level tag: end paragraph before the tag, start new paragraph after it!
            # TODO currently fails:
            # ("a<hr>_break_", '<p>a</p><separator html:class="moin-hr3" /><p><emphasis>break</emphasis></p>'),
            # ("a<hr />_break_", '<p>a</p><separator html:class="moin-hr3" /><p><emphasis>break</emphasis></p>'),
            # (
            #     "a\n<hr>\n_break_",
            #     '<p>a</p><separator html:class="moin-hr3" />\n<p><emphasis>break</emphasis></p>',
            # ),
            # ("_a_<hr>break", '<p><emphasis>a</emphasis></p><separator html:class="moin-hr3" /><p>break</p>'),
            # ("_a_<hr>\nbreak", '<p><emphasis>a</emphasis></p><separator html:class="moin-hr3" />\n<p>break</p>'),
        ],
    )
    def test_html_markup(self, input, output):
        """Test handling of HTML markup."""
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            ('<a href="subitem">link text</a>', '<p><a xlink:href="wiki.local:subitem">link text</a></p>'),
            (  # & may be given as literal or entity
                '<a href="http:example.org?num=20&amp;q=top&x=u">query</a>',
                '<p><a xlink:href="http:example.org?num=20&amp;q=top&amp;x=u">query</a></p>',
            ),
            ('<a class="selected">no href</a>', '<p><a html:class="selected">no href</a></p>'),
            ("<BIG>larger</BIG>", '<p><span html:class="moin-big">larger</span></p>'),
            ('<span class="moin-small">smaller</span>', '<p><span html:class="moin-small">smaller</span></p>'),
            ("<sub>sub</sub>script", "<p><sub>sub</sub>script</p>"),
            ("<sup>super</sup>script", "<p><sup>super</sup>script</p>"),
            ("<code>Code</code>", "<p><code>Code</code></p>"),
            ("<em>Emphasis</em>", "<p><emphasis>Emphasis</emphasis></p>"),
            ("<i>alternate voice</i>", '<p><emphasis html-tag="i">alternate voice</emphasis></p>'),
            ("<u>underline</u>", "<p><u>underline</u></p>"),
            ("<ins>inserted</ins>", "<p><ins>inserted</ins></p>"),
            ("<kbd>Ctrl-X</kbd>", "<p><kbd>Ctrl-X</kbd></p>"),
            ("<samp>Error 33</samp>", "<p><samp>Error 33</samp></p>"),
            ("<tt>literal</tt>", "<p><literal>literal</literal></p>"),
            ("<del>deleted</del>", "<p><del>deleted</del></p>"),
            ("<s>no longer accurate</s>", "<p><s>no longer accurate</s></p>"),
            # the <strike> tag is deprecated since HTML4.1!
            ("<strike>obsolete</strike>", "<p><s>obsolete</s></p>"),
            ("<q>Inline quote</q>", "<p><quote>Inline quote</quote></p>"),
            ("<dfn>term</dfn>", '<p><emphasis html-tag="dfn">term</emphasis></p>'),
            ("<small>fine print</small>", '<p><span html-tag="small">fine print</span></p>'),
            ("<abbr>e.g.</abbr>", '<p><span html-tag="abbr">e.g.</span></p>'),
            # keep standard attributes "title", "class", "style", and "alt":
            ('<del class="red">deleted</del>', '<p><del html:class="red">deleted</del></p>'),
            (
                '<abbr title="for example">e.g.</abbr>',
                '<p><span html-tag="abbr" html:title="for example">e.g.</span></p>',
            ),
            # in HTML5, <acronym> is deprecated in favour of <abbr>
            ("<acronym>AC/DC</acronym>", '<p><span html-tag="abbr">AC/DC</span></p>'),
            # <br> is a void inline element
            ("one<br />two", "<p>one<line-break />two</p>"),
            ("one<br>two", "<p>one<line-break />two</p>"),
            ("one<br />\ntwo", "<p>one<line-break />\ntwo</p>"),
            ("one  \ntwo", "<p>one<line-break />\ntwo</p>"),
            # <br> do not break the paragraph if preceded or followed by Markdown markup
            ("one<br>_two_", "<p>one<line-break /><emphasis>two</emphasis></p>"),
            ("one<br>\n_two_", "<p>one<line-break />\n<emphasis>two</emphasis></p>"),
            ("_one_<br>two", "<p><emphasis>one</emphasis><line-break />two</p>"),
            ("_one_<br>\ntwo", "<p><emphasis>one</emphasis><line-break />\ntwo</p>"),
            # there may be multiple HTML elements in a block
            ("<u>underline</u> and <sub>sub</sub>", "<p><u>underline</u> and <sub>sub</sub></p>"),
            ("<u>underline with <sub>sub</sub></u>", "<p><u>underline with <sub>sub</sub></u></p>"),
        ],
    )
    def test_inline_html(self, input, output):
        self.do(input, output)

    @pytest.mark.parametrize(
        "input,output",
        [
            (  # Original issue #1838: emphasis inside <del> in a list item
                "* <del>Deleted list item with _emphasized text_</del>",
                '<list item-label-generate="unordered"><list-item><list-item-body>'
                "<del>Deleted list item with <emphasis>emphasized text</emphasis></del>"
                "</list-item-body></list-item></list>",
            ),
            (
                '<a href="subitem">link *text*</a>',
                '<p><a xlink:href="wiki.local:subitem">link <emphasis>text</emphasis></a></p>',
            ),
            (
                '<abbr title="for example">_e.g._</abbr>',
                '<p><span html-tag="abbr" html:title="for example"><emphasis>e.g.</emphasis></span></p>',
            ),
            ("<acronym>**AC/DC**</acronym>", '<p><span html-tag="abbr"><strong>AC/DC</strong></span></p>'),
            ("<BIG>_larger_</BIG>", '<p><span html:class="moin-big"><emphasis>larger</emphasis></span></p>'),
            ("<ins>Inserted with _emphasis_</ins>", "<p><ins>Inserted with <emphasis>emphasis</emphasis></ins></p>"),
            ("<kbd>Press **Q**</kbd>", "<p><kbd>Press <strong>Q</strong></kbd></p>"),
            ("<DEL>`1+1`</DEL>", "<p><del><code>1+1</code></del></p>"),
            ("<dfn>**strong** term</dfn>", '<p><emphasis html-tag="dfn"><strong>strong</strong> term</emphasis></p>'),
            ("<i>alternate **voice**</i>", '<p><emphasis html-tag="i">alternate <strong>voice</strong></emphasis></p>'),
            ("<small>`fine` print</small>", '<p><span html-tag="small"><code>fine</code> print</span></p>'),
            ("<tt>**mono**</tt>", "<p><literal><strong>mono</strong></literal></p>"),
            # Attention: Markdown markup in <code> is processed:
            ("<code>2*3*4</code>", "<p><code>2<emphasis>3</emphasis>4</code></p>"),
            ("<code><em>important</em></code>", "<p><code><emphasis>important</emphasis></code></p>"),
            # explicitly ignored tags are dropped together with their content:
            ("<button>`Stop`</button>", "<p />"),
            # unknown tags are ignored but their content is passed on:
            ("<custom>`1+1`</custom>", "<p><code>1+1</code></p>"),
            # there may be multiple HTML elements in a block
            (
                "<u>**strong underline**</u> and <sub>sub</sub>",
                "<p><u><strong>strong underline</strong></u> and <sub>sub</sub></p>",
            ),
            (
                "<u>underline</u> and <sub>**strong sub**</sub>",
                "<p><u>underline</u> and <sub><strong>strong sub</strong></sub></p>",
            ),
            (
                "<u>**underline**</u> and <sub>**sub**</sub>",
                "<p><u><strong>underline</strong></u> and <sub><strong>sub</strong></sub></p>",
            ),
        ],
    )
    def test_inline_html_with_embedded_markdown(self, input, output):
        """Test HTML markup containing Markdown markup"""
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}):
        conv = Converter()
        out = conv(input, "text/x-markdown;charset=utf-8", **args)
        got_output = self.serialize_strip(out)
        desired_output = "<page><body>%s</body></page>" % output
        print("------------------------------------")
        print("WANTED:")
        print(desired_output)
        print("GOT:")
        print(got_output)
        assert got_output == desired_output
