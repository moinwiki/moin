# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.wikiutil tests.
"""

from __future__ import annotations

import pytest

from flask import current_app as app
from moin import wikiutil
from moin.wikiutil import WikiLinkAnalyzer, WikiLinkInfo
from typing import cast


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


def test_ParentItemName():
    # with no parent
    result = wikiutil.ParentItemName("itemname")
    expected = ""
    assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()
    # with a parent
    result = wikiutil.ParentItemName("some/parent/itemname")
    expected = "some/parent"
    assert result == expected


def test_getUnicodeIndexGroup():
    result = wikiutil.getUnicodeIndexGroup(["moin-2", "MoinMoin"])
    expected = "MOIN-2"
    assert result == expected
    # empty char
    with pytest.raises(IndexError):
        result = wikiutil.getUnicodeIndexGroup("")


def test_is_URL():
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


def test_containsConflictMarker():
    # text with conflict marker
    result = wikiutil.containsConflictMarker("/!\\ '''Edit conflict - Conflict marker is present")
    assert result

    # text without conflict marker
    result = wikiutil.containsConflictMarker("No conflict marker")
    assert not result


def test_file_headers():
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


@pytest.mark.usefixtures("_app_ctx")
@pytest.mark.parametrize(
    "url,expected",
    [
        # internal item links
        ("users/roland", WikiLinkInfo(True, "frontend.show_item", "users/roland")),
        ("+index/all", WikiLinkInfo(True, "frontend.index", "all", True)),
        ("+history/users/roland", WikiLinkInfo(True, "frontend.history", "users/roland")),
        # internal global link (not linking to a wiki item)
        ("all", WikiLinkInfo(True, "frontend.global_views", None, True)),
        # link without matching moin route
        ("+invalid/help", WikiLinkInfo(False)),
        # external link
        ("http://google.com/hello", WikiLinkInfo(False)),
    ],
)
def test_classify_link(url, expected):
    link_analyzer = cast(WikiLinkAnalyzer, app.link_analyzer)
    result = link_analyzer(url)
    assert result == expected


coverage_modules = ["moin.wikiutil"]
