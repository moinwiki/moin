# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.moinwiki19_in
"""


import pytest

from MoinMoin.converter.moinwiki19_in import ConverterFormat19

from test_moinwiki_in import TestConverter as _Base


class TestConverterFormat19(_Base):
    def setup_class(self):
        self.conv = ConverterFormat19()

    def test_freelink(self):
        data = [
            (u'MoinMoin',
                '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
            (u'!MoinMoin',
                '<page><body><p>MoinMoin</p></body></page>'),
            (u'Self:FrontPage',
                '<page><body><p><a xlink:href="wiki://Self/FrontPage">FrontPage</a></p></body></page>'),
            (u'http://moinmo.in/',
                '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>'),
            # email tests
            (u'mailto:foo@bar.baz',
                '<page><body><p><a xlink:href="mailto:foo@bar.baz">mailto:foo@bar.baz</a></p></body></page>'),
            (u'foo@bar.baz',
                '<page><body><p><a xlink:href="mailto:foo@bar.baz">foo@bar.baz</a></p></body></page>'),
            (u'foo@bar',  # 1.9 requires domain
                '<page><body><p>foo@bar</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i
