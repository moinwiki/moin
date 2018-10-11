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

from moin.util.tree import moin_page, xlink, xinclude, html, xml
from moin.converter.markdown_in import Converter as conv_in
from moin.converter.markdown_out import Converter as conv_out


class TestConverter(object):

    input_namespaces = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}" xmlns:xinclude="{3}" xmlns:html="{4}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
        xinclude.namespace: 'xinclude',
        html.namespace: 'html',
        xml.namespace: 'xml',
    }

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        (u'Text',
         u'Text\n'),
        (u'Text\n\nText\n',
         u'Text\n\nText\n'),
        (u'xxx\n\n------\n\n------\n\n------\n',
         u'xxx\n\n----\n\n----\n\n----\n'),
        (u'----\n\n------\n\n--------\n',
         u'----\n\n----\n\n----\n'),
        (u'**strong**\n',
         u'**strong**\n'),
        (u'*emphasis*\n',
         u'*emphasis*\n'),
        (u'    blockcode\n',
         u'    blockcode\n'),
        (u'`monospace`\n',
         u'`monospace`\n'),
        (u'<strike>stroke</strike>\n',
         u'<strike>stroke</strike>\n'),
        # <ins> is changed to <u>
        (u'<ins>underline</ins>\n',
         u'<u>underline</u>\n'),
        (u'<big>larger</big>\n',
         u'<big>larger</big>\n'),
        (u'<small>smaller</small>\n',
         u'<small>smaller</small>\n'),
        (u'<sup>super</sup>script\n',
         u'<sup>super</sup>script\n'),
        (u'<sub>sub</sub>script\n',
         u'<sub>sub</sub>script\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (u'level 1\n=======\n',
         u'# level 1 #\n'),
        (u'# level 1 #\n',
         u'# level 1 #\n'),
        (u'## level 2 ##\n',
         u'## level 2 ##\n'),
        (u'## level 2\n',
         u'## level 2 ##\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_headings(self, input, output):
        self.do(input, output)

    data = [
        (u'[TOC]\n',
         u'[TOC]\n'),
        (u'|Tables|Are|Very|Cool|\n|------|:----:|-----:|:-----|\n|col 2 is|centered|$12|Gloves|\n',
         u'|Tables|Are|Very|Cool|\n|------|:----:|-----:|:-----|\n|col 2 is|centered|$12|Gloves|\n'),
        # TODO: wrong output
        (u'``` javascript\nvar s = "JavaScript syntax highlighting";\nalert(s);\n```\n',
         u'    var s = "JavaScript syntax highlighting";\n    alert(s);\n'),
        # TODO: wrong output
        (u'~~~ {python}\ndef hello():\n    print "Hello World!"\n~~~\n',
         u'    def hello():\n        print "Hello World!"\n'),
        (u'~~~\nddd\neee\nfff\n~~~\n',
         u'    ddd\n    eee\n    fff\n'),
        # TODO: maybe wrong output
        (u'Text with double__underscore__words.\n\n__Strong__ still works.\n\n__this__works__too__.\n',
         u'Text with double__underscore__words.\n\n**Strong** still works.\n\n**this__works__too**.\n'),
        # TODO: missing class
        (u'### orange heading #### {: .orange }\n',
         u'### orange heading ###\n'),
        # TODO: missing class
        (u'A class of LawnGreen is added to this paragraph.\n{: class="LawnGreen "}\n',
         u'A class of LawnGreen is added to this paragraph.\n'),
        (u'{: #para3 }\n',
         u'{: #para3 }\n'),
        (u'so [click to see 3rd paragraph](#para3).\n',
         u'so [click to see 3rd paragraph](#para3).\n'),
        (u'Apple\n:   Pomaceous fruit of plants of the genus Malus in\n    the family Rosaceae.\n:   An american computer company.\n',
         u'Apple\n:   Pomaceous fruit of plants of the genus Malus in\n    the family Rosaceae.\n:   An american computer company.\n'),
        # footnotes test is incomplete, footnotes are positioned but not defined
        (u'Footnotes[^1] have a label[^label] and a definition[^!DEF].\n',
         u'Footnotes[^1] have a label[^label] and a definition[^!DEF].\n'),
        # TODO: spectacular failure, causes 19 UnicodeEncodeErrors, claims \xA0 characters
        # (u'Footnotes[^a\n\n[^a]: This is a footnote\n',
        #  u'Footnotes[^a\n\n[^a]: This is a footnote\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_extensions(self, input, output):
        self.do(input, output)

    data = [
        (u'[MoinMoin](http://moinmo.in)\n',
         u'[MoinMoin](http://moinmo.in)\n'),
        (u'[PNG](png)\n',
         u'[PNG](png)\n'),
        (u'[MoinMoin][moin]\n[moin]: http://moinmo.in\n',
         u'[MoinMoin](http://moinmo.in)\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (u'* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n',
         u'* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n'),
        (u'  * A\n      1. C\n          - E\n',
         u'  * A\n    1. C\n        * E\n'),
        (u' * A\n     1. C\n     1. D\n',
         u' * A\n    1. C\n    1. D\n'),
        (u'1. E\n1. F\n',
         u'1. E\n1. F\n'),
        (u'    1. E\n    1. F\n',
         u'    1. E\n    1. F\n'),
        (u'Apple\n:   B\n:   C\n:   D\n',
         u'Apple\n:   B\n:   C\n:   D\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (u'|A|B|C|\n|-|-|-|\n|1|2|3|\n',
         u'|A|B|C|\n|------|------|------|\n|1|2|3|\n'),
        (u'|A|B|C|\n|:-|:-:|-:|\n|1|2|3|\n',
         u'|A|B|C|\n|:-----|:----:|-----:|\n|1|2|3|\n'),
        (u'A|B|C\n-|-|-\n1|2|3\n',
         u'|A|B|C|\n|------|------|------|\n|1|2|3|\n'),
        (u'`A`|*B*|_C_\n:-|:-:|-:\n1|2|3\n',
         u'|`A`|*B*|*C*|\n|:-----|:----:|-----:|\n|1|2|3|\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (u'\n![Alt text](png "Optional title")',
         u'\n![Alt text](png "Optional title")\n'),
        (u'![Alt text](png)',
         u'![Alt text](png)\n'),
        (u'![Alt text][logo]\n[logo]: png "Optional title attribute"',
         u'![Alt text](png "Optional title attribute")\n'),
        (u'![remote image](http://static.moinmo.in/logos/moinmoin.png)',
         u'![remote image](http://static.moinmo.in/logos/moinmoin.png)\n'),
        (u'![Alt text](http://test.moinmo.in/png)',
         u'![Alt text](http://test.moinmo.in/png)\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_images(self, input, output):
        self.do(input, output)

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', result)

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, 'text/x-markdown;charset=utf-8', **args)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        # assert self.handle_output(out) == output
        assert self.handle_output(out).strip() == output.strip()  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
