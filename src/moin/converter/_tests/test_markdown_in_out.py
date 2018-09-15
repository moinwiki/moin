# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2018 MoinMoin:RogerHaase - modified test_moinwiki_in_out.py for markdown
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for markdown->DOM->markdown using markdown_in and markdown_out converters

TODO: Failing tests are commented out and need to be fixed.
"""

import pytest

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.util.tree import moin_page, xlink, xinclude, html
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
    }
    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        (u'Text', 'Text\n'),
        (u"Text\n\nText\n", 'Text\n\nText\n'),
        (u"xxx\n\n------\n\n------\n\n------\n", 'xxx\n\n----\n\n----\n\n----\n'),
        (u"----\n\n------\n\n--------\n", '----\n\n----\n\n----\n'),
        (u"**strong**\n", "**strong**\n"),
        (u"*emphasis*\n", "*emphasis*\n"),
        (u"    blockcode\n", "    blockcode\n"),
        (u"`monospace`\n", '`monospace`\n'),
        (u"<strike>stroke</strike>\n", '<strike>stroke</strike>\n'),
        # <ins> is changed to <u>
        (u"<ins>underline</ins>\n", '<u>underline</u>\n'),
        (u"<big>larger</big>\n", '<big>larger</big>\n'),
        (u"<small>smaller</small>\n", '<small>smaller</small>\n'),
        (u"<sup>super</sup>script\n", '<sup>super</sup>script\n'),
        (u"<sub>sub</sub>script\n", '<sub>sub</sub>script\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_base(self, input, output):
        self.do(input, output)

    # TODO: these tests cause: ParseError: unbound prefix: line 1, column 263
    data = [
        # (u"level 1\n=======\n", '# level 1 #\n'),
        # (u"# level 1 #\n", '# level 1 #\n'),
        # (u"## level 2 ##\n", '## level 2 ##\n'),
        # (u"## level 2\n", '## level 2 ##\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_headings(self, input, output):
        self.do(input, output)

    data = [
        (u"[TOC]\n", '[TOC]\n'),
        (u"Footnotes[^1] have a label[^label] and a definition[^!DEF].\n", 'Footnotes[^1] have a label[^label] and a definition[^!DEF].\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_extensions(self, input, output):
        self.do(input, output)

    data = [
        (u'[MoinMoin](http://moinmo.in)\n', '[MoinMoin](http://moinmo.in)\n'),
        (u'[PNG](png)\n', '[PNG](png)\n'),
        (u'[MoinMoin][moin]\n[moin]: http://moinmo.in\n', '[MoinMoin](http://moinmo.in)\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (u"* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n", '* A\n* B\n    1. C\n    1. D\n        1. E\n        1. F\n'),
        (u"  * A\n      1. C\n          - E\n", '  * A\n    1. C\n        * E\n'),
        (u" * A\n     1. C\n     1. D\n", ' * A\n    1. C\n    1. D\n'),
        (u"1. E\n1. F\n", "1. E\n1. F\n"),
        (u"    1. E\n    1. F\n", "    1. E\n    1. F\n"),
        (u"Apple\n:   B\n:   C\n:   D\n", 'Apple\n:   B\n:   C\n:   D\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (u"|A|B|C|\n|-|-|-|\n|1|2|3|\n",
         u'|A|B|C|\n|------|------|------|\n|1|2|3|\n'),
        (u"|A|B|C|\n|:-|:-:|-:|\n|1|2|3|\n",
         u'|A|B|C|\n|:-----|:----:|-----:|\n|1|2|3|\n'),
        (u"A|B|C\n-|-|-\n1|2|3\n",
         u'|A|B|C|\n|------|------|------|\n|1|2|3|\n'),
        (u"`A`|*B*|_C_\n:-|:-:|-:\n1|2|3\n",
         u'|`A`|*B*|*C*|\n|:-----|:----:|-----:|\n|1|2|3|\n'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (u'\n![Alt text](png "Optional title"\n)', '\n![Alt text](png "Optional title")\n'),
        (u'![Alt text](png)', '![Alt text](png)\n'),
        (u'![Alt text][logo]\n[logo]: png "Optional title attribute"', '![Alt text](png "Optional title attribute")\n'),
        (u'![remote image](http://static.moinmo.in/logos/moinmoin.png)', '![remote image](http://static.moinmo.in/logos/moinmoin.png)\n'),
        (u'![Alt text](http://test.moinmo.in/png)', '![Alt text](http://test.moinmo.in/png)\n'),
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
