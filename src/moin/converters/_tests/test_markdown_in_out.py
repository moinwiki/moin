# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2018 MoinMoin:RogerHaase - modified test_moinwiki_in_out.py for markdown
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for Markdown->DOM->Markdown using markdown_in and markdown_out converters
"""

import pytest

from collections import namedtuple
from flask import Flask

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.utils.tree import moin_page, xlink, xinclude, html, xml
from moin.converters.markdown_in import Converter as ConverterIn
from moin.converters.markdown_out import Converter as ConverterOut


DefaultConfig = namedtuple("DefaultConfig", ("markdown_extensions",))
config = DefaultConfig(markdown_extensions=[])


@pytest.fixture
def _app_context_with_markdown_extensions_config():
    """
    A fixture providing an application context with just the Moin2 configuration
    settings required by the markdown_in_out converter.
    """
    app = Flask(__name__)
    app.cfg = config
    with app.app_context() as context:
        yield context


@pytest.mark.usefixtures("_app_context_with_markdown_extensions_config")
class TestConverter:

    input_namespaces = 'xmlns="{}" xmlns:page="{}" xmlns:xlink="{}" xmlns:xinclude="{}" xmlns:html="{}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace
    )

    namespaces = {
        moin_page.namespace: "page",
        xlink.namespace: "xlink",
        xinclude.namespace: "xinclude",
        html.namespace: "html",
        xml.namespace: "xml",
    }

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    data = [
        ("Text", "Text\n"),
        ("Text\n\nText\n", "Text\n\nText\n"),
        ("xxx\n\n------\n\n------\n\n------\n", "xxx\n\n----\n\n----\n\n----\n"),
        ("----\n\n------\n\n--------\n", "----\n\n----\n\n----\n"),
        ("**strong**\n", "**strong**\n"),
        ("*emphasis*\n", "*emphasis*\n"),
        ("    blockcode\n", "    blockcode\n"),
        ("`monospace`\n", "`monospace`\n"),
        ("<abbr>etc.</abbr>", "<abbr>etc.</abbr>"),
        ("<acronym>DC</acronym>", "<abbr>DC</abbr>"),  # in HTML5, <acronym> is deprecated in favour of <abbr>
        ("<cite>Winnie-the-Pooh</cite>", "<cite>Winnie-the-Pooh</cite>"),
        ("<dfn>term</dfn>", "<dfn>term</dfn>"),
        ("<strike>stroke</strike>\n", "<s>stroke</s>\n"),  # <strike> is obsolete since HTML 4.1
        ("<ins>inserted</ins>\n", "<ins>inserted</ins>\n"),
        ("<del>deleted</del>\n", "<del>deleted</del>\n"),
        ("<u>annotated</u>\n", "<u>annotated</u>\n"),
        ("<s>no longer accurate</s>\n", "<s>no longer accurate</s>\n"),
        ("<kbd>Ctrl-X</kbd><", "<kbd>Ctrl-X</kbd><"),
        ("see <mark>here</mark>", "see <mark>here</mark>"),
        ("<q>cogito ergo sum</q>", "<q>cogito ergo sum</q>"),
        ("<big>larger</big>\n", "<big>larger</big>\n"),
        ("<small>fine print</small>\n", "<small>fine print</small>\n"),
        ('<span class="red" id="dwarf">star</span>', '<span class="red" id="dwarf">star</span>'),
        ("<sup>super</sup>script\n", "<sup>super</sup>script\n"),
        ("<sub>sub</sub>script\n", "<sub>sub</sub>script\n"),
        ("<var>n</var> times\n", "<var>n</var> times\n"),
        ("<hr>\n\n<hr>\n\n<hr>\n", "----\n\n----\n\n----\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        ("level 1\n=======\n", "# level 1 #\n"),
        ("# level 1 #\n", "# level 1 #\n"),
        ("## level 2 ##\n", "## level 2 ##\n"),
        ("## level 2\n", "## level 2 ##\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_headings(self, input, output):
        self.do(input, output)

    data = [
        ("[TOC]\n", "[TOC]\n"),
        (
            "|Tables|Are|Very|Cool|\n|------|:----:|-----:|:-----|\n|col 2 is|centered|$12|Gloves|\n",
            "|Tables|Are|Very|Cool|\n|------|:----:|-----:|:-----|\n|col 2 is|centered|$12|Gloves|\n",
        ),
        # TODO: wrong output, creates indented blockcode, loses fenced code language
        # fix probably requires replacing site-packages/markdown/extensions/codehilite.py
        (
            '``` javascript\nvar s = "JavaScript syntax highlighting";\nalert(s);\n```\n',
            '    var s = "JavaScript syntax highlighting";\n    alert(s);\n',
        ),
        # TODO: wrong output, creates indented blockcode, loses fenced code language
        (
            '~~~ python\ndef hello():\n    print "Hello World!"\n~~~\n',
            '    def hello():\n        print "Hello World!"\n',
        ),
        ("~~~\nddd\neee\nfff\n~~~\n", "    ddd\n    eee\n    fff\n"),
        (
            "Text with double__underscore__words.\n\n__Strong__ still works.\n\n__this__works__too__.\n",
            "Text with double__underscore__words.\n\n**Strong** still works.\n\n**this__works__too**.\n",
        ),
        ("### orange heading ### {: .orange }\n", '### orange heading ### {: class="orange"}\n'),
        (
            'A class of LawnGreen is added to this paragraph.\n{: class="LawnGreen"}\n',
            'A class of LawnGreen is added to this paragraph.\n{: class="LawnGreen"}\n',
        ),
        ("{: #para3 }\n", "{: #para3 }\n"),
        ("so [click to see 3rd paragraph](#para3).\n", "so [click to see 3rd paragraph](#para3).\n"),
        (
            "Apple\n:   Pomaceous fruit of plants of the genus Malus in\n    the family Rosaceae.\n:   An american computer company.\n",
            "Apple\n:   Pomaceous fruit of plants of the genus Malus in\n    the family Rosaceae.\n:   An american computer company.\n",
        ),
        # incomplete footnote test, footnotes are positioned but not defined
        (
            "Footnotes[^1] have a label[^label] and a definition[^!DEF].\n",
            "Footnotes[^1] have a label[^label] and a definition[^!DEF].\n",
        ),
        # TODO: test footnote placement succeeds but output is wrong, and other tests will fail due to pytest multithreading
        # fix probably requires replacing site-packages/markdown/extensions/footnotes.py
        # ('Footnotes[^a]\n\n[^a]: This is a footnote.\n',
        #  'Footnotes<sup>1</sup>\n\n----\n\n1. This is a footnote.\xa0[\u21a9](#fnref:a){: class="footnote-backref" title="Jump back to footnote 1 in the text"}\n'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_extensions(self, input, output):
        self.do(input, output)

    data = [
        ("[MoinMoin](http://moinmo.in)\n", "[MoinMoin](http://moinmo.in)\n"),
        ("[PNG](png)\n", "[PNG](png)\n"),
        ("[MoinMoin][moin]\n[moin]: http://moinmo.in\n", "[MoinMoin](http://moinmo.in)\n"),
        ('[![Image name](png)](Home "click me")', '[![Image name](png)](Home "click me")'),
        ("[toc](#table-of-contents)", "[toc](#table-of-contents)"),
        ("[toc](markdown#table-of-contents)", "[toc](markdown#table-of-contents)"),
        ('[moinmoin](https://moinmo.in "Go there")', '[moinmoin](https://moinmo.in "Go there")'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (
            "* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n",
            "* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n",
        ),
        ("  * A\n      1. C\n          - E\n", "  * A\n    1. C\n        * E\n"),
        (" * A\n     1. C\n     1. D\n", " * A\n    1. C\n    1. D\n"),
        ("1. E\n1. F\n", "1. E\n1. F\n"),
        ("    1. E\n    1. F\n", "    1. E\n    1. F\n"),
        ("Apple\n:   B\n:   C\n:   D\n", "Apple\n:   B\n:   C\n:   D\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        ("|A|B|C|\n|-|-|-|\n|1|2|3|\n", "|A|B|C|\n|------|------|------|\n|1|2|3|\n"),
        ("|A|B|C|\n|:-|:-:|-:|\n|1|2|3|\n", "|A|B|C|\n|:-----|:----:|-----:|\n|1|2|3|\n"),
        ("A|B|C\n-|-|-\n1|2|3\n", "|A|B|C|\n|------|------|------|\n|1|2|3|\n"),
        ("`A`|*B*|_C_\n:-|:-:|-:\n1|2|3\n", "|`A`|*B*|*C*|\n|:-----|:----:|-----:|\n|1|2|3|\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        ('\n![Alt text](png "Optional title")', '\n![Alt text](png "Optional title")\n'),
        ("![Alt text](png)", "![Alt text](png)\n"),
        ('![Alt text][logo]\n[logo]: png "Optional title attribute"', '![Alt text](png "Optional title attribute")\n'),
        # alt defined twice
        (
            "![remote image](http://static.moinmo.in/logos/moinmoin.png)",
            '![remote image](http://static.moinmo.in/logos/moinmoin.png){: alt="remote image"}\n',
        ),
        # alt defined twice
        ("![Alt text](http://test.moinmo.in/png)", '![Alt text](http://test.moinmo.in/png){: alt="Alt text"}\n'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_images(self, input, output):
        self.do(input, output)

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}):
        conv_in = ConverterIn()
        out = conv_in(input, "text/x-markdown;charset=utf-8", **args)
        conv_out = ConverterOut()
        out = conv_out(self.handle_input(self.serialize_strip(out)), **args)
        # assert self.handle_output(out) == output
        assert (
            self.handle_output(out).strip() == output.strip()
        )  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
