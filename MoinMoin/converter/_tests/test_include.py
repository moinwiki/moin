# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.include
"""


import pytest

from MoinMoin.converter.include import *
from MoinMoin.items import MoinWiki
from MoinMoin.config import CONTENTTYPE
from MoinMoin._tests import wikiconfig, update_item

class TestInclude(object):
    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_XPointer(self):
        x = XPointer('a')
        assert len(x) == 1
        e = x[0]
        assert e.name == 'a'
        assert e.data is None

        x = XPointer('a(b)')
        assert len(x) == 1
        e = x[0]
        assert e.name == 'a'
        assert e.data == 'b'

        x = XPointer('a(^(b^)^^)')
        assert len(x) == 1
        e = x[0]
        assert e.name == 'a'
        assert e.data == '^(b^)^^'
        assert e.data_unescape == '(b)^'

        x = XPointer('a(b)c(d)')
        assert len(x) == 2
        e = x[0]
        assert e.name == 'a'
        assert e.data == 'b'
        e = x[1]
        assert e.name == 'c'
        assert e.data == 'd'

        x = XPointer('a(b) c(d)')
        assert len(x) == 2
        e = x[0]
        assert e.name == 'a'
        assert e.data == 'b'
        e = x[1]
        assert e.name == 'c'
        assert e.data == 'd'

        x = XPointer('a(a(b))')
        assert len(x) == 1
        e = x[0]
        assert e.name == 'a'
        assert e.data == 'a(b)'

    def test_IncludeHandlesCircularRecursion(self):
        # issue #80
        # we choosed MoinWiki items so tests get simpler
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page2}}')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page3}}')
        update_item(u'page3', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page1}}')

        page1 = MoinWiki.create(u'page1')

        page1._render_data()
