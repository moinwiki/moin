"""
    MoinMoin - MoinMoin.wikiutil Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 by MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import py

from flask import current_app as app

from MoinMoin import config, wikiutil
from MoinMoin._tests import wikiconfig

from werkzeug import MultiDict


class TestCleanInput(object):
    def testCleanInput(self):
        tests = [(u"", u""), # empty
                 (u"aaa\r\n\tbbb", u"aaa   bbb"), # ws chars -> blanks
                 (u"aaa\x00\x01bbb", u"aaabbb"), # strip weird chars
                 (u"a"*500, u""), # too long
                ]
        for instr, outstr in tests:
            assert wikiutil.clean_input(instr) == outstr


class TestSystemItem(object):
    systemItems = (
        'HelpOnMoinWikiSyntax',
        'HelpOnLinking',
        )
    notSystemItems = (
        'NoSuchPageYetAndWillNeverBe',
        )

    class Config(wikiconfig.Config):
        load_xml = wikiconfig.Config._test_items_xml

    def testSystemItem(self):
        """wikiutil: good system item names accepted, bad rejected"""
        for name in self.systemItems:
            assert wikiutil.isSystemItem(name)
        for name in self.notSystemItems:
            assert not wikiutil.isSystemItem(name)


class TestAnchorNames(object):
    def test_anchor_name_encoding(self):
        tests = [
            # text                    expected output
            (u'\xf6\xf6ll\xdf\xdf',   'A.2BAPYA9g-ll.2BAN8A3w-'),
            (u'level 2',              'level_2'),
            (u'level_2',              'level_2'),
            (u'',                     'A'),
            (u'123',                  'A123'),
            # make sure that a valid anchor is not modified:
            (u'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_.-',
             u'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_.-')
        ]
        for text, expected in tests:
            yield self._check, text, expected

    def _check(self, text, expected):
        encoded = wikiutil.anchor_name_from_text(text)
        assert expected == encoded


class TestRelativeTools(object):
    tests = [
        # test                      expected output
        # CHILD_PREFIX
        (('MainPage', '/SubPage1'), 'MainPage/SubPage1'),
        (('MainPage', '/SubPage1/SubPage2'), 'MainPage/SubPage1/SubPage2'),
        (('MainPage/SubPage1', '/SubPage2/SubPage3'), 'MainPage/SubPage1/SubPage2/SubPage3'),
        (('', '/OtherMainPage'), 'OtherMainPage'), # strange
        # PARENT_PREFIX
        (('MainPage/SubPage', '../SisterPage'), 'MainPage/SisterPage'),
        (('MainPage/SubPage1/SubPage2', '../SisterPage'), 'MainPage/SubPage1/SisterPage'),
        (('MainPage/SubPage1/SubPage2', '../../SisterPage'), 'MainPage/SisterPage'),
        (('MainPage', '../SisterPage'), 'SisterPage'), # strange
    ]
    def test_abs_pagename(self):
        for (current_page, relative_page), absolute_page in self.tests:
            yield self._check_abs_pagename, current_page, relative_page, absolute_page

    def _check_abs_pagename(self, current_page, relative_page, absolute_page):
        assert absolute_page == wikiutil.AbsItemName(current_page, relative_page)

    def test_rel_pagename(self):
        for (current_page, relative_page), absolute_page in self.tests:
            yield self._check_rel_pagename, current_page, absolute_page, relative_page

    def _check_rel_pagename(self, current_page, absolute_page, relative_page):
        assert relative_page == wikiutil.RelItemName(current_page, absolute_page)


class TestNormalizePagename(object):

    def testPageInvalidChars(self):
        """ request: normalize pagename: remove invalid unicode chars

        Assume the default setting
        """
        test = u'\u0000\u202a\u202b\u202c\u202d\u202e'
        expected = u''
        result = wikiutil.normalize_pagename(test, app.cfg)
        assert result == expected

    def testNormalizeSlashes(self):
        """ request: normalize pagename: normalize slashes """
        cases = (
            (u'/////', u''),
            (u'/a', u'a'),
            (u'a/', u'a'),
            (u'a/////b/////c', u'a/b/c'),
            (u'a b/////c d/////e f', u'a b/c d/e f'),
            )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected

    def testNormalizeWhitespace(self):
        """ request: normalize pagename: normalize whitespace """
        cases = (
            (u'         ', u''),
            (u'    a', u'a'),
            (u'a    ', u'a'),
            (u'a     b     c', u'a b c'),
            (u'a   b  /  c    d  /  e   f', u'a b/c d/e f'),
            # All 30 unicode spaces
            (config.chars_spaces, u''),
            )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected

    def testUnderscoreTestCase(self):
        """ request: normalize pagename: underscore convert to spaces and normalized

        Underscores should convert to spaces, then spaces should be
        normalized, order is important!
        """
        cases = (
            (u'         ', u''),
            (u'  a', u'a'),
            (u'a  ', u'a'),
            (u'a  b  c', u'a b c'),
            (u'a  b  /  c  d  /  e  f', u'a b/c d/e f'),
            )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected

class TestGroupItems(object):

    def testNormalizeGroupName(self):
        """ request: normalize itemname: restrict groups to alpha numeric Unicode

        Spaces should normalize after invalid chars removed!
        """
        cases = (
            # current acl chars
            (u'Name,:Group', u'NameGroup'),
            # remove than normalize spaces
            (u'Name ! @ # $ % ^ & * ( ) + Group', u'Name Group'),
            )
        for test, expected in cases:
            # validate we are testing valid group names
            if wikiutil.isGroupItem(test):
                result = wikiutil.normalize_pagename(test, app.cfg)
                assert result == expected


coverage_modules = ['MoinMoin.wikiutil']

