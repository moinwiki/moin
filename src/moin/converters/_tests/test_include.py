# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.include
"""


from moin.converters.include import XPointer
from moin.items import Item
from moin.constants.keys import CONTENTTYPE, ACL
from moin._tests import wikiconfig, update_item


class TestInclude:
    class Config(wikiconfig.Config):
        """
        we just have this so the test framework creates a new app with empty backends for us.
        """

    def test_XPointer(self):
        x = XPointer("a")
        assert len(x) == 1
        e = x[0]
        assert e.name == "a"
        assert e.data is None

        x = XPointer("a(b)")
        assert len(x) == 1
        e = x[0]
        assert e.name == "a"
        assert e.data == "b"

        x = XPointer("a(^(b^)^^)")
        assert len(x) == 1
        e = x[0]
        assert e.name == "a"
        assert e.data == "^(b^)^^"
        assert e.data_unescape == "(b)^"

        x = XPointer("a(b)c(d)")
        assert len(x) == 2
        e = x[0]
        assert e.name == "a"
        assert e.data == "b"
        e = x[1]
        assert e.name == "c"
        assert e.data == "d"

        x = XPointer("a(b) c(d)")
        assert len(x) == 2
        e = x[0]
        assert e.name == "a"
        assert e.data == "b"
        e = x[1]
        assert e.name == "c"
        assert e.data == "d"

        x = XPointer("a(a(b))")
        assert len(x) == 1
        e = x[0]
        assert e.name == "a"
        assert e.data == "a(b)"

    def test_IncludeHandlesCircularRecursion(self):
        # detect circular recursion and create error message
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{page2}}")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{page3}}")
        update_item("page3", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{page4}}")
        update_item("page4", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{page2}}")
        page1 = Item.create("page1")
        rendered = page1.content._render_data()
        # an error message will follow strong tag
        assert '<strong class="moin-error">' in rendered

    def test_Include_Read_Permission_Denied(self):
        # attempt to include an item that user cannot read
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8", ACL: "All:write,create,admin,destroy"},
            "no one can read",
        )
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "some text{{page1}}more text")
        page2 = Item.create("page2")
        rendered = page2.content._render_data()
        # an error message will follow p tag, similar to: Access Denied, transcluded content suppressed.
        assert '<div class="warning moin-read-denied"><p>' in rendered

    def test_ExternalInclude(self):
        # external include
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{http://moinmo.in}}")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<object class="moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object>'
            in rendered
        )
        # external include embedded within text (object is an inline tag)
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "before {{http://moinmo.in}} after")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before <object class="moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object> after</p>'
            in rendered
        )
        # external include embedded within text italic and bold markup (object is an inline tag)
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"},
            "before ''italic '''bold {{http://moinmo.in}} bold''' italic'' normal",
        )
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before <em>italic <strong>bold <object class="moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object> bold</strong> italic</em> normal</p>'
            in rendered
        )

    def test_InlineInclude(self):

        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "before {{page2}} after")
        # transclude single paragraph as inline
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Single line")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before <span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en">Single line</span> after</p>'
            in rendered
        )
        # transclude multiple paragraphs as block
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Two\n\nParagraphs")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before </p><div class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"><p>Two</p><p>Paragraphs</p></div><p> after</p></div>'
            in rendered
        )
        # transclude single paragraph with internal markup as inline
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "this text contains ''italic'' string")
        rendered = Item.create("page1").content._render_data()
        assert (
            'before <span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en">this text contains <em>italic</em>'
            in rendered
        )
        # transclude single paragraph as only content within a paragraph
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Content of page2 is\n\n{{page2}}")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Single Line")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>Content of page2 is</p><p><span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en">Single Line</span></p>'
            in rendered
        )
        # transclude single row table within a paragraph, block element forces paragraph to be split into 2 parts
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "before {{page2}} after")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "|| table || cell ||")
        rendered = Item.create("page1").content._render_data()
        assert '<p>before </p><div class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"><table' in rendered
        assert "</table></div><p> after</p>" in rendered
        assert rendered.count("<table") == 1
        # transclude two row table within a paragraph, block element forces paragraph to be split into 2 parts
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "before {{page2}} after")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "|| this || has ||\n|| two || rows ||")
        rendered = Item.create("page1").content._render_data()
        # inclusion of block item within a paragraph results in a before and after p
        assert '<p>before </p><div class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"><table' in rendered
        assert "</table></div><p> after</p>" in rendered
        assert rendered.count("<table") == 1
        # transclude nonexistent item
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "before {{nonexistent}} after")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before <span class="moin-transclusion" data-href="/nonexistent" dir="ltr" lang="en"><a href="/+modify/nonexistent">'
            in rendered
        )
        assert "</a></span> after</p>" in rendered
        # transclude empty item
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text {{page2}} text")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"></span> text</p></div>'
            in rendered
        )

    def test_InlineIncludeCreole(self):
        # transclude single paragraph as inline using creole parser
        update_item("creole", {CONTENTTYPE: "text/x.moin.creole;charset=utf-8"}, "creole item")
        update_item("page1", {CONTENTTYPE: "text/x.moin.creole;charset=utf-8"}, "before {{creole}} after")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>before <span class="moin-transclusion" data-href="/creole" dir="ltr" lang="en">creole item</span> after</p>'
            in rendered
        )

    def test_InlineIncludeWithinMarkup(self):
        # transclude single line item within italic and bold markup
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"},
            "Normal ''italic '''bold {{page2}} bold''' italic'' normal",
        )
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Single Line")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>Normal <em>italic <strong>bold <span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en">Single Line</span> bold</strong> italic</em> normal</p>'
            in rendered
        )
        # transclude double line item within italic and bold markup
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"},
            "Normal ''italic '''bold {{page2}} bold''' italic'' normal",
        )
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Double\n\nLine")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>Normal <em>italic <strong>bold </strong></em></p><div class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"><p>Double</p><p>Line</p></div><p><em><strong> bold</strong> italic</em> normal</p>'
            in rendered
        )
        # transclude single line item within comment
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "comment /* before {{page2}} after */")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Single Line")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>comment <span class="comment">before <span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en">Single Line</span> after</span></p>'
            in rendered
        )
        # transclude double line item within comment
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "comment /* before {{page2}} after */")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Double\n\nLine")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>comment <span class="comment">before </span></p><div class="comment moin-transclusion" data-href="/page2" dir="ltr" lang="en"><p>Double</p><p>Line</p></div><p><span class="comment"> after</span></p>'
            in rendered
        )

    def test_InlineIncludeImage(self):
        # the 3rd parameter, '',  should be a binary string defining a png image, but it is not needed for this simple test
        update_item("logo.png", {CONTENTTYPE: "image/png"}, "")
        # simple transclusion
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{logo.png}}")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src='
            in rendered
        )
        assert '/logo.png" /></span></p>' in rendered
        # simple transclusion with alt text and width
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, '{{logo.png|my alt text|width="100"}}')
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="my alt text" src='
            in rendered
        )
        assert 'logo.png" width="100" /></span></p>' in rendered
        # within paragraph
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text {{logo.png}} text")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src='
            in rendered
        )
        assert '/logo.png" /></span> text</p>' in rendered
        # within markup
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"},
            "Normal ''italic '''bold {{logo.png}} bold''' italic'' normal",
        )
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>Normal <em>italic <strong>bold <span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src='
            in rendered
        )
        assert '/logo.png" /></span> bold</strong> italic</em> normal</p>' in rendered
        # multiple transclusions
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "{{logo.png}}{{logo.png}}")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src='
            in rendered
        )
        assert (
            '/logo.png" /></span><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src='
            in rendered
        )
        # check for old bug
        assert "<p />" not in rendered
        assert "<p></p>" not in rendered

    def test_IncludeAsLinkAlternate(self):
        # the 3rd parameter, '',  should be a binary string defining a png image, but it is not needed for this simple test
        update_item("logo.png", {CONTENTTYPE: "image/png"}, "")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Single Line")
        # image as link alternate
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[page2|{{logo.png}}]] text")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a href="/page2"><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src="'
            in rendered
        )
        assert '/logo.png" /></span></a> text</p>' in rendered
        # link alternate with image embedded in markup
        update_item(
            "page1",
            {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"},
            "text [[page2|plain '''bold {{logo.png}} bold''' plain]] text",
        )
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a href="/page2">plain <strong>bold <span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src="'
            in rendered
        )
        assert '/logo.png" /></span> bold</strong> plain</a> text</p>' in rendered
        # nonexistent image used in link alternate
        # XXX html validation errora: A inside A - the image alternate turns into an A-tag to create the non-existant image.  Error is easily seen.
        # IE9, Firefox, Chrome, Safari, and Opera display this OK;  the only usable hyperlink is to create the missing image.
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[page2|{{logoxxx.png}}]] text")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a href="/page2"><span class="moin-transclusion" data-href="/logoxxx.png" dir="ltr" lang="en"><a href="/+modify/logoxxx.png">'
            in rendered
        )
        assert "</a></span></a> text</p>" in rendered
        # image used as alternate to nonexistent page
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[page2xxx|{{logo.png}}]] text")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a class="moin-nonexistent" href="/page2xxx"><span class="moin-transclusion" data-href="/logo.png" dir="ltr" lang="en"><img alt="logo.png" src="'
            in rendered
        )
        assert '/logo.png" /></span></a> text</p>' in rendered
        # transclude block elem as link alternate to nonexistent page
        # XXX html validation errors, block element inside A.
        # IE9, Firefox, Chrome, Safari, and Opera display this OK;  the hyperlink is the entire div enclosing the block elem
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[MyPage|{{page2}}]] text")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "Double\n\nLine")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a class="moin-nonexistent" href="/MyPage"><div class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"><p>Double</p><p>Line</p></div></a> text</p>'
            in rendered
        )
        # transclude empty item as link alternate to nonexistent page
        # hyperlink will be empty span and invisible
        update_item("page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[MyPage|{{page2}}]] text")
        update_item("page2", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "")
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a class="moin-nonexistent" href="/MyPage"><span class="moin-transclusion" data-href="/page2" dir="ltr" lang="en"></span></a> text</p>'
            in rendered
        )
        # transclude external page as link alternate to nonexistent page
        update_item(
            "page1", {CONTENTTYPE: "text/x.moin.wiki;charset=utf-8"}, "text [[MyPage|{{http://moinmo.in}}]] text"
        )
        rendered = Item.create("page1").content._render_data()
        assert (
            '<p>text <a class="moin-nonexistent" href="/MyPage"><object class="moin-transclusion" data="http://moinmo.in" data-href="http://moinmo.in">http://moinmo.in</object></a> text</p>'
            in rendered
        )
