# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.include
"""


import pytest

from MoinMoin.converter.include import *
from MoinMoin.items import Item
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
        # we use text/x.moin.wiki markup to make tests simple
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page2}}')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page3}}')
        update_item(u'page3', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page4}}')
        update_item(u'page4', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page2}}')

        page1 = Item.create(u'page1')
        rendered = page1.content._render_data()
        # an error message will follow strong tag
        assert '<strong class="moin-error">' in rendered

    def test_ExternalInclude(self):
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{http://moinmo.in}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<object class="moin-http moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object>' in rendered

    def test_InlineInclude(self):
        # issue #28
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Content of page2 is "{{page2}}".')

        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Single line')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Content of page2 is "<span class="moin-transclusion" data-href="/page2">Single line</span>".</p>' in rendered

        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Two\n\nParagraphs')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Content of page2 is "</p><div class="moin-transclusion" data-href="/page2"><p>Two</p><p>Paragraphs</p></div><p>".</p></div>' in rendered

        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"this text contains ''italic'' string")
        rendered = Item.create(u'page1').content._render_data()
        assert 'Content of page2 is "<span class="moin-transclusion" data-href="/page2">this text contains <em>italic</em>' in rendered

        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Content of page2 is\n\n{{page2}}')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Single Line")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Content of page2 is</p><p><span class="moin-transclusion" data-href="/page2">Single Line</span></p>' in rendered

        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Content of page2 is "{{page2}}"')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"|| table || cell ||")
        rendered = Item.create(u'page1').content._render_data()
        assert 'Content of page2 is "</p>' in rendered
        assert '<table>' in rendered
        assert rendered.count('<table>') == 1

        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Content of page2 is "{{page2}}"')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"|| this || has ||\n|| two || rows ||")
        rendered = Item.create(u'page1').content._render_data()
        assert 'Content of page2 is "</p>' in rendered
        assert '<table>' in rendered
        assert rendered.count('<table>') == 1

    def test_InlineIncludeLogo(self):
        # the 3rd parameter, u'',  should be a binary string defining a png image, but it is not needed for this simple test
        update_item(u'logo', {CONTENTTYPE: u'image/png'}, u'')

        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{logo}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<img alt="logo" class="moin-transclusion"' in rendered

        # <p /> is not valid html5; should be <p></p>. to be valid.  Even better, there should be no empty p's.
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{logo}}{{logo}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p />' not in rendered
        assert '<p></p>' not in rendered
