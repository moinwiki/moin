# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moinwiki->DOM->moinwiki using moinwiki19_in and moinwiki_out converters.

The use of moinwiki19_in converter rather than moinwiki_in converter does not
matter so long as moinwiki19_in is limited to CamelCase linking conversions.

TODO: Merge this back into test_moinwiki_in_out.py.
"""


import pytest
import re

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE

from moin.util.tree import moin_page, xlink, xinclude, html
from moin.converter.moinwiki19_in import ConverterFormat19 as conv_in
from moin.converter.moinwiki_out import Converter as conv_out


class TestConverter(object):

    input_namespaces = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}" xmlns:xinclude="{3}" xmlns:html="{4}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
        xinclude.namespace: 'xinclude',
        html.namespace: 'html',
    }
    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        # no arguments
        (u'{{{#!python\nimport sys\n}}}', u'{{{#!python\nimport sys\n}}}'),
        (u'{{{#!creole\n... **bold** ...\n}}}', u'{{{#!creole\n... **bold** ...\n}}}'),
        # old style arguments
        (u'{{{#!csv ,\nA,B\n1,2\n}}}', u'{{{#!csv ,\nA,B\n1,2\n}}}'),
        (u'{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}',
         u'{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}'),
        (u'{{{#!wiki red/solid\nThis is wiki markup in a """div""" with __css__ `class="red solid"`.\n}}}',
         u'{{{#!wiki red/solid\nThis is wiki markup in a """div""" with __css__ `class="red solid"`.\n}}}'),
        # new style arguments
        (u'{{{#!wiki (style="color: green")\nThis is wiki markup in a """div""" with `style="color: green"`.\n}}}',
         u'{{{#!wiki (style="color: green")\nThis is wiki markup in a """div""" with `style="color: green"`.\n}}}'),
        (u'{{{#!wiki (style="color: green")\ngreen\n}}}', u'{{{#!wiki (style="color: green")\ngreen\n}}}'),
        (u'{{{#!wiki (style="color: green" class="dotted")\ngreen\n}}}',
         u'{{{#!wiki (style="color: green" class="dotted")\ngreen\n}}}'),
        # multi-level
        (u'{{{#!wiki green\ngreen\n{{{{#!wiki orange\norange\n}}}}\ngreen\n}}}',
         u'{{{#!wiki green\ngreen\n{{{{#!wiki orange\norange\n}}}}\ngreen\n}}}'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_parsers(self, input, output):
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
        out = self.conv_in(input, 'text/x.moin.wiki;format=1.9;charset=utf-8', **args)
        print '=== type(out) = %s' % type(out)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        assert self.handle_output(out).strip() == output.strip()  # TODO: remove .strip() when number of \n between blocks in moinwiki_out.py is stable
