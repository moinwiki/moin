# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2017 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moinwiki19 -> DOM -> moinwiki using moinwiki19_in and moinwiki_out converters.

Copied from test_moinwiki_in_out.py, modified to use ConverterFormat19 -> DOM.

This same conversion is used in the "moin import19 ..." command to convert deprecated
Moin 1.9 markup to Moin 2.0 markup.
"""

import pytest

# TODO: failing tests are commented out and need to be fixed

from emeraldtree import ElementTree as ET

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.converters.moinwiki19_in import ConverterFormat19 as conv_in
from moin.converters.moinwiki_out import Converter as conv_out


class TestConverter:

    input_namespaces = 'xmlns="{}" xmlns:page="{}" xmlns:xlink="{}" xmlns:xinclude="{}" xmlns:html="{}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace
    )

    namespaces = {
        moin_page.namespace: "page",
        xlink.namespace: "xlink",
        xinclude.namespace: "xinclude",
        html.namespace: "html",
    }
    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        # Note: old style attachments are are supported in moinwiki_in so conversion to moin 2 markup is not necessary
        # TODO: in a perfect world, moinwiki19_in should convert attachments
        ("[[attachment:filename.txt]]", "[[/filename.txt]]\n"),
        # moin 1.9 to 2.0 conversion
        ("TestPage", "[[TestPage]]\n"),
        # ('../SisterPage', '[[../SisterPage]]\n'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
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
        out = self.conv_in(input, "text/x.moin.wiki;format=1.9;charset=utf-8", **args)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        assert self.handle_output(out) == output
