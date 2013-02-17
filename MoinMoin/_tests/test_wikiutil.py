# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.wikiutil Tests
"""


import pytest

from flask import current_app as app

from MoinMoin.constants.chartypes import CHARS_SPACES
from MoinMoin import wikiutil

from werkzeug import MultiDict


class TestCleanInput(object):
    def testCleanInput(self):
        tests = [(u"", u""),  # empty
                 (u"aaa\r\n\tbbb", u"aaa   bbb"),  # ws chars -> blanks
                 (u"aaa\x00\x01bbb", u"aaabbb"),  # strip weird chars
                 (u"a" * 500, u""),  # too long
                ]
        for instr, outstr in tests:
            assert wikiutil.clean_input(instr) == outstr


class TestAnchorNames(object):
    def test_anchor_name_encoding(self):
        tests = [
            # text, expected output
            (u'\xf6\xf6ll\xdf\xdf', 'A.2BAPYA9g-ll.2BAN8A3w-'),
            (u'level 2', 'level_2'),
            (u'level_2', 'level_2'),
            (u'', 'A'),
            (u'123', 'A123'),
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
        (('', '/OtherMainPage'), 'OtherMainPage'),  # strange
        # PARENT_PREFIX
        (('MainPage/SubPage', '../SisterPage'), 'MainPage/SisterPage'),
        (('MainPage/SubPage1/SubPage2', '../SisterPage'), 'MainPage/SubPage1/SisterPage'),
        (('MainPage/SubPage1/SubPage2', '../../SisterPage'), 'MainPage/SisterPage'),
        (('MainPage', '../SisterPage'), 'SisterPage'),  # strange
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
            (CHARS_SPACES, u''),
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


def testParentItemName():
    # with no parent
    result = wikiutil.ParentItemName(u'itemname')
    expected = u''
    assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()
    # with a parent
    result = wikiutil.ParentItemName(u'some/parent/itemname')
    expected = u'some/parent'
    assert result == expected


def testdrawing2fname():
    # with extension not in DRAWING_EXTENSIONS
    result = wikiutil.drawing2fname('Moin_drawing.txt')
    expected = 'Moin_drawing.txt.tdraw'
    assert result == expected
    # with extension in DRAWING_EXTENSIONS
    result = wikiutil.drawing2fname('Moindir.Moin_drawing.jpg')
    expected = 'Moindir.Moin_drawing.jpg'
    assert result == expected


def testgetUnicodeIndexGroup():
    result = wikiutil.getUnicodeIndexGroup(['moin-2', 'MoinMoin'])
    expected = 'MOIN-2'
    assert result == expected
    # empty char
    with pytest.raises(IndexError):
        result = wikiutil.getUnicodeIndexGroup('')


def testis_URL():
    sample_schemes = ['http', 'https', 'ftp', 'ssh']
    for scheme in sample_schemes:
        result = wikiutil.is_URL(scheme + ':MoinMoin')
        assert result

    # arg without ':' which is a mandatory requirement
    result = wikiutil.is_URL('MoinMoin')
    assert not result
    # invalid scheme
    result = wikiutil.is_URL('invalid_scheme:MoinMoin')
    assert not result


def testcontainsConflictMarker():
    # text with conflict marker
    result = wikiutil.containsConflictMarker("/!\\ '''Edit conflict - Conflict marker is present")
    assert result

    #text without conflict marker
    result = wikiutil.containsConflictMarker('No conflict marker')
    assert not result


def testsplit_anchor():
    """
    TODO: add the test for for split_anchor when we have better
          approach to deal wih problems like "#MoinMoin#" returning ("#MoinMoin", "")
    """
    result = wikiutil.split_anchor('MoinMoin')
    expected = 'MoinMoin', ''
    assert result == expected

    result = wikiutil.split_anchor('MoinMoin#test_anchor|label|attr=val')
    expected = ['MoinMoin', 'test_anchor|label|attr=val']
    assert result == expected

    result = wikiutil.split_anchor('#MoinMoin#')
    expected = ['#MoinMoin', '']
    assert result == expected


def testfile_headers():
    test_headers = [
                #test_file, content_type
                ('imagefile.gif', 'image/gif'),
                ('testfile.txt', 'text/plain'),
                ('pdffile.pdf', 'application/pdf'),
                ('docfile.doc', 'application/msword'),
                (None, 'application/octet-stream')
                ]

    for test_file, content_type in test_headers:
        result = wikiutil.file_headers(test_file, None, 10)
        expected = [('Content-Type', content_type), ('Content-Length', '10')]
        assert result == expected

    # filename is none and content type has a value
    result = wikiutil.file_headers(None, 'text/plain')
    expected = [('Content-Type', 'text/plain')]
    assert result == expected


coverage_modules = ['MoinMoin.wikiutil']
