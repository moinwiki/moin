# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.moinwiki19_in
"""


import pytest

from . import serialize, XMLNS_RE

from moin.converters.moinwiki19_in import ConverterFormat19
from moin.utils.tree import moin_page, xlink, html, xinclude


class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", html: "xhtml", xinclude: "xinclude"}

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = ConverterFormat19()

    data = [
        ("MoinMoin", '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
        ("!MoinMoin", "<page><body><p>MoinMoin</p></body></page>"),
        ("Self:FrontPage", '<page><body><p><a xlink:href="wiki://Self/FrontPage">FrontPage</a></p></body></page>'),
        (
            "http://moinmo.in/",
            '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>',
        ),
        # email tests
        (
            "mailto:foo@bar.baz",
            '<page><body><p><a xlink:href="mailto:foo@bar.baz">mailto:foo@bar.baz</a></p></body></page>',
        ),
        ("foo@bar.baz", '<page><body><p><a xlink:href="mailto:foo@bar.baz">foo@bar.baz</a></p></body></page>'),
        ("foo@bar", "<page><body><p>foo@bar</p></body></page>"),  # 1.9 requires domain
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_freelink(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv(input, "text/x.moin.wiki;charset=utf-8", **args)
        assert self.serialize_strip(out) == output
