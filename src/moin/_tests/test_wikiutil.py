# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.wikiutil Tests
"""


import pytest

from flask import current_app as app

from moin.constants.chartypes import CHARS_SPACES
from moin import wikiutil


class TestCleanInput:
    def testCleanInput(self):
        tests = [
            ("", ""),  # empty
            ("aaa\r\n\tbbb", "aaa   bbb"),  # ws chars -> blanks
            ("aaa\x00\x01bbb", "aaabbb"),  # strip weird chars
            ("a" * 500, ""),  # too long
        ]
        for instr, outstr in tests:
            assert wikiutil.clean_input(instr) == outstr


class TestAnchorNames:
    @pytest.mark.parametrize(
        "text,expected",
        [
            # old note: recent werkzeug encodes a "+" to "%2B", giving ".2B" in the end,
            #       also "-" to "%2D", giving ".2D".
            # ('\xf6\xf6ll\xdf\xdf', 'A.2BAPYA9g.2Dll.2BAN8A3w.2D'),
            #                                   ^^^           ^^^
            # -----------
            # newer note:
            # see #1496 'werkzeug.urls.url_quote_plus' is deprecated. Use 'urllib.parse.quote' instead.
            # Contrary to werkzeug, urllib does not do: 'also "-" to "%2D", giving ".2D".'
            ("\xf6\xf6ll\xdf\xdf", "A.2BAPYA9g-ll.2BAN8A3w-"),
            #                                 ^           ^
            ("level 2", "level_2"),
            ("level_2", "level_2"),
            ("", "A"),
            ("123", "A123"),
            # make sure that a valid anchor is not modified:
            (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_.",
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_.",
            ),
        ],
    )
    def test_anchor_name_encoding(self, text, expected):
        encoded = wikiutil.anchor_name_from_text(text)
        assert expected == encoded


class TestRelativeTools:
    tests = [
        # test                      expected output
        # CHILD_PREFIX
        ("MainPage", "/SubPage1", "MainPage/SubPage1"),
        ("MainPage", "/SubPage1/SubPage2", "MainPage/SubPage1/SubPage2"),
        ("MainPage/SubPage1", "/SubPage2/SubPage3", "MainPage/SubPage1/SubPage2/SubPage3"),
        ("", "/OtherMainPage", "OtherMainPage"),  # strange
        # PARENT_PREFIX
        ("MainPage/SubPage", "../SisterPage", "MainPage/SisterPage"),
        ("MainPage/SubPage1/SubPage2", "../SisterPage", "MainPage/SubPage1/SisterPage"),
        ("MainPage/SubPage1/SubPage2", "../../SisterPage", "MainPage/SisterPage"),
        ("MainPage", "../SisterPage", "SisterPage"),  # strange
    ]

    @pytest.mark.parametrize("current_page,relative_page,absolute_page", tests)
    def test_abs_pagename(self, current_page, relative_page, absolute_page):
        assert absolute_page == wikiutil.AbsItemName(current_page, relative_page)

    @pytest.mark.parametrize("current_page,relative_page,absolute_page", tests)
    def test_rel_pagename(self, current_page, relative_page, absolute_page):
        assert relative_page == wikiutil.RelItemName(current_page, absolute_page)


class TestNormalizePagename:

    def testPageInvalidChars(self):
        """request: normalize pagename: remove invalid unicode chars

        Assume the default setting
        """
        test = "\u0000\u202a\u202b\u202c\u202d\u202e"
        expected = ""
        result = wikiutil.normalize_pagename(test, app.cfg)
        assert result == expected

    def testNormalizeSlashes(self):
        """request: normalize pagename: normalize slashes"""
        cases = (
            ("/////", ""),
            ("/a", "a"),
            ("a/", "a"),
            ("a/////b/////c", "a/b/c"),
            ("a b/////c d/////e f", "a b/c d/e f"),
        )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected

    def testNormalizeWhitespace(self):
        """request: normalize pagename: normalize whitespace"""
        cases = (
            ("         ", ""),
            ("    a", "a"),
            ("a    ", "a"),
            ("a     b     c", "a b c"),
            ("a   b  /  c    d  /  e   f", "a b/c d/e f"),
            # All 30 unicode spaces
            (CHARS_SPACES, ""),
        )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected

    def testUnderscoreTestCase(self):
        """request: normalize pagename: underscore convert to spaces and normalized

        Underscores should convert to spaces, then spaces should be
        normalized, order is important!
        """
        cases = (
            ("         ", ""),
            ("  a", "a"),
            ("a  ", "a"),
            ("a  b  c", "a b c"),
            ("a  b  /  c  d  /  e  f", "a b/c d/e f"),
        )
        for test, expected in cases:
            result = wikiutil.normalize_pagename(test, app.cfg)
            assert result == expected


class TestGroupItems:

    def testNormalizeGroupName(self):
        """request: normalize itemname: restrict groups to alpha numeric Unicode

        Spaces should normalize after invalid chars removed!
        """
        cases = (
            # current acl chars
            ("Name,:Group", "NameGroup"),
            # remove than normalize spaces
            ("Name ! @ # $ % ^ & * ( ) + Group", "Name Group"),
        )
        for test, expected in cases:
            # validate we are testing valid group names
            if wikiutil.isGroupItem(test):
                result = wikiutil.normalize_pagename(test, app.cfg)
                assert result == expected


def testParentItemName():
    # with no parent
    result = wikiutil.ParentItemName("itemname")
    expected = ""
    assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()
    # with a parent
    result = wikiutil.ParentItemName("some/parent/itemname")
    expected = "some/parent"
    assert result == expected


def testdrawing2fname():
    # with extension not in DRAWING_EXTENSIONS
    result = wikiutil.drawing2fname("Moin_drawing.txt")
    expected = "Moin_drawing.txt.svgdraw"
    assert result == expected
    # with extension in DRAWING_EXTENSIONS
    result = wikiutil.drawing2fname("Moindir.Moin_drawing.jpg")
    expected = "Moindir.Moin_drawing.jpg"
    assert result == expected


def testgetUnicodeIndexGroup():
    result = wikiutil.getUnicodeIndexGroup(["moin-2", "MoinMoin"])
    expected = "MOIN-2"
    assert result == expected
    # empty char
    with pytest.raises(IndexError):
        result = wikiutil.getUnicodeIndexGroup("")


def testis_URL():
    sample_schemes = ["http", "https", "ftp", "ssh"]
    for scheme in sample_schemes:
        result = wikiutil.is_URL(scheme + ":MoinMoin")
        assert result

    # arg without ':' which is a mandatory requirement
    result = wikiutil.is_URL("MoinMoin")
    assert not result
    # invalid scheme
    result = wikiutil.is_URL("invalid_scheme:MoinMoin")
    assert not result


def testcontainsConflictMarker():
    # text with conflict marker
    result = wikiutil.containsConflictMarker("/!\\ '''Edit conflict - Conflict marker is present")
    assert result

    # text without conflict marker
    result = wikiutil.containsConflictMarker("No conflict marker")
    assert not result


def testsplit_anchor():
    """
    TODO: add the test for for split_anchor when we have better
          approach to deal wih problems like "#MoinMoin#" returning ("#MoinMoin", "")
    """
    result = wikiutil.split_anchor("MoinMoin")
    expected = "MoinMoin", ""
    assert result == expected

    result = wikiutil.split_anchor("MoinMoin#test_anchor|label|attr=val")
    expected = ["MoinMoin", "test_anchor|label|attr=val"]
    assert result == expected

    result = wikiutil.split_anchor("#MoinMoin#")
    expected = ["#MoinMoin", ""]
    assert result == expected


def testfile_headers():
    test_headers = [
        # test_file, content_type
        ("imagefile.gif", "image/gif"),
        ("testfile.txt", "text/plain"),
        ("pdffile.pdf", "application/pdf"),
        ("docfile.doc", "application/msword"),
        (None, "application/octet-stream"),
    ]

    for test_file, content_type in test_headers:
        result = wikiutil.file_headers(test_file, None, 10)
        expected = [("Content-Type", content_type), ("Content-Length", "10")]
        assert result == expected

    # filename is none and content type has a value
    result = wikiutil.file_headers(None, "text/plain")
    expected = [("Content-Type", "text/plain")]
    assert result == expected


coverage_modules = ["moin.wikiutil"]
