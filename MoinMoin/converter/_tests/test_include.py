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
        # detect circular recursion and create error message
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page2}}')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page3}}')
        update_item(u'page3', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page4}}')
        update_item(u'page4', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{page2}}')
        page1 = Item.create(u'page1')
        rendered = page1.content._render_data()
        # an error message will follow strong tag
        assert '<strong class="moin-error">' in rendered

    def test_ExternalInclude(self):
        # external include
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{http://moinmo.in}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<object class="moin-http moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object>' in rendered
        # external include embedded within text (object is an inline tag)
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'before {{http://moinmo.in}} after')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before <object class="moin-http moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object> after</p>' in rendered
        # external include embedded within text italic and bold markup (object is an inline tag)
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"before ''italic '''bold {{http://moinmo.in}} bold''' italic'' normal")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before <em>italic <strong>bold <object class="moin-http moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object> bold</strong> italic</em> normal</p>' in rendered

    def test_InlineInclude(self):

        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'before {{page2}} after')
        # transclude single paragraph as inline
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Single line')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before <span class="moin-transclusion" data-href="/page2">Single line</span> after</p>' in rendered
        # transclude multiple paragraphs as block
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Two\n\nParagraphs')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before </p><div class="moin-transclusion" data-href="/page2"><p>Two</p><p>Paragraphs</p></div><p> after</p></div>' in rendered
        # transclude single paragraph with internal markup as inline
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"this text contains ''italic'' string")
        rendered = Item.create(u'page1').content._render_data()
        assert 'before <span class="moin-transclusion" data-href="/page2">this text contains <em>italic</em>' in rendered
        # transclude single paragraph as only content within a paragraph
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'Content of page2 is\n\n{{page2}}')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Single Line")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Content of page2 is</p><p><span class="moin-transclusion" data-href="/page2">Single Line</span></p>' in rendered
        # transclude single row table within a paragraph, block element forces paragraph to be split into 2 parts
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'before {{page2}} after')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"|| table || cell ||")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before </p><div class="moin-transclusion" data-href="/page2"><table' in rendered
        assert '</table></div><p> after</p>' in rendered
        assert rendered.count('<table>') == 1
        # transclude two row table within a paragraph, block element forces paragraph to be split into 2 parts
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'before {{page2}} after')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"|| this || has ||\n|| two || rows ||")
        rendered = Item.create(u'page1').content._render_data()
        # inclusion of block item within a paragraph results in a before and after p
        assert '<p>before </p><div class="moin-transclusion" data-href="/page2"><table' in rendered
        assert '</table></div><p> after</p>' in rendered
        assert rendered.count('<table>') == 1
        # transclude nonexistent item
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'before {{nonexistent}} after')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before <span class="moin-transclusion" data-href="/nonexistent"><a href="/+modify/nonexistent">' in rendered
        assert '</a></span> after</p>' in rendered
        # transclude empty item
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'text {{page2}} text')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <span class="moin-transclusion" data-href="/page2"></span> text</p>' in rendered
    def test_InlineIncludeCreole(self):
        # transclude single paragraph as inline using creole parser
        update_item(u'creole', {CONTENTTYPE: u'text/x.moin.creole;charset=utf-8'}, u'creole item')
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.creole;charset=utf-8'}, u'before {{creole}} after')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>before <span class="moin-transclusion" data-href="/creole">creole item</span> after</p>' in rendered
    def test_InlineIncludeWithinMarkup(self):
        # transclude single line item within italic and bold markup
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Normal ''italic '''bold {{page2}} bold''' italic'' normal")
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Single Line")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Normal <em>italic <strong>bold <span class="moin-transclusion" data-href="/page2">Single Line</span> bold</strong> italic</em> normal</p>' in rendered
        # transclude double line item within italic and bold markup
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Normal ''italic '''bold {{page2}} bold''' italic'' normal")
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Double\n\nLine")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Normal <em>italic <strong>bold </strong></em></p><div class="moin-transclusion" data-href="/page2"><p>Double</p><p>Line</p></div><p><em><strong> bold</strong> italic</em> normal</p>' in rendered
        # transclude single line item within comment
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"comment /* before {{page2}} after */")
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Single Line")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>comment <span class="comment">before <span class="moin-transclusion" data-href="/page2">Single Line</span> after</span></p>' in rendered
        # transclude double line item within comment
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"comment /* before {{page2}} after */")
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Double\n\nLine")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>comment <span class="comment">before </span></p><div class="comment moin-transclusion" data-href="/page2"><p>Double</p><p>Line</p></div><p><span class="comment"> after</span></p>' in rendered

    def test_InlineIncludeImage(self):
        # the 3rd parameter, u'',  should be a binary string defining a png image, but it is not needed for this simple test
        update_item(u'logo.png', {CONTENTTYPE: u'image/png'}, u'')
        # simple transclusion
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{logo.png}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p><span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src=' in rendered
        assert '/logo.png" /></span></p>' in rendered
        # within paragraph
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'text {{logo.png}} text')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src=' in rendered
        assert '/logo.png" /></span> text</p>' in rendered
        # within markup
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Normal ''italic '''bold {{logo.png}} bold''' italic'' normal")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>Normal <em>italic <strong>bold <span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src=' in rendered
        assert '/logo.png" /></span> bold</strong> italic</em> normal</p>' in rendered
        # multiple transclusions
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'{{logo.png}}{{logo.png}}')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p><span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src=' in rendered
        assert '/logo.png" /></span><span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src=' in rendered
        # check for old bug
        assert '<p />' not in rendered
        assert '<p></p>' not in rendered

    def test_IncludeAsLinkAlternate(self):
        # image as link alternate
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"text [[page2|{{logo.png}}]] text")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a href="/page2"><span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src="' in rendered
        assert '/logo.png" /></span></a> text</p>' in rendered
        # link alternate with image embedded in markup
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"text [[page2|plain '''bold {{logo.png}} bold''' plain]] text")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a href="/page2">plain <strong>bold <span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src="' in rendered
        assert '/logo.png" /></span> bold</strong> plain</a> text</p>' in rendered
        # nonexistent image used in link alternate
        # XXX html validation errora: A inside A - the image alternate turns into an A-tag to create the non-existant image.  Error is easily seen.
        # IE9, Firefox, Chrome, Safari, and Opera display this OK;  the only usable hyperlink is to create the missing image.
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"text [[page2|{{logoxxx.png}}]] text")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a href="/page2"><span class="moin-transclusion" data-href="/logoxxx.png"><a href="/+modify/logoxxx.png">' in rendered
        assert '</a></span></a> text</p>' in rendered
        # image used as alternate to nonexistent page
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u"text [[page2xxx|{{logo.png}}]] text")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a class="moin-nonexistent" href="/page2xxx"><span class="moin-transclusion" data-href="/logo.png"><img alt="logo.png" src="' in rendered
        assert '/logo.png" /></span></a> text</p>' in rendered
        # transclude block elem as link alternate to nonexistent page
        # XXX html validation errors, block element inside A.
        # IE9, Firefox, Chrome, Safari, and Opera display this OK;  the hyperlink is the entire div enclosing the block elem
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'text [[MyPage|{{page2}}]] text')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"Double\n\nLine")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a class="moin-nonexistent" href="/MyPage"><div class="moin-transclusion" data-href="/page2"><p>Double</p><p>Line</p></div></a> text</p>' in rendered
        # transclude empty item as link alternate to nonexistent page
        # hyperlink will be empty span and invisible
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'text [[MyPage|{{page2}}]] text')
        update_item(u'page2', {CONTENTTYPE: u'text/x.moin.wiki'}, u"")
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a class="moin-nonexistent" href="/MyPage"><span class="moin-transclusion" data-href="/page2"></span></a> text</p>' in rendered
        # transclude external page as link alternate to nonexistent page
        update_item(u'page1', {CONTENTTYPE: u'text/x.moin.wiki'}, u'text [[MyPage|{{http://moinmo.in}}]] text')
        rendered = Item.create(u'page1').content._render_data()
        assert '<p>text <a class="moin-nonexistent" href="/MyPage"><object class="moin-http moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object></a> text</p>' in rendered
