# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2018 MoinMoin:RogerHaase - modified test_moinwiki_in_out.py for markdown
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for markdown->DOM->markdown using markdown_in and markdown_out converters
"""

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.utils.tree import moin_page, xlink, xinclude, html, xml
from moin.converters.markdown_in import Converter as conv_in
from moin.converters.markdown_out import Converter as conv_out


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

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        ("Text", "Text\n"),
        ("Text\n\nText\n", "Text\n\nText\n"),
        ("xxx\n\n------\n\n------\n\n------\n", "xxx\n\n----\n\n----\n\n----\n"),
        ("----\n\n------\n\n--------\n", "----\n\n----\n\n----\n"),
        ("**strong**\n", "**strong**\n"),
        ("*emphasis*\n", "*emphasis*\n"),
        ("    blockcode\n", "    blockcode\n"),
        ("`monospace`\n", "`monospace`\n"),
        ("<strike>stroke</strike>\n", "<strike>stroke</strike>\n"),
        # <ins> is changed to <u>
        ("<ins>underline</ins>\n", "<u>underline</u>\n"),
        ("<big>larger</big>\n", "<big>larger</big>\n"),
        ("<small>smaller</small>\n", "<small>smaller</small>\n"),
        ("<sup>super</sup>script\n", "<sup>super</sup>script\n"),
        ("<sub>sub</sub>script\n", "<sub>sub</sub>script\n"),
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
            '~~~ {python}\ndef hello():\n    print "Hello World!"\n~~~\n',
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

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, "text/x-markdown;charset=utf-8", **args)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        # assert self.handle_output(out) == output
        assert (
            self.handle_output(out).strip() == output.strip()
        )  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
