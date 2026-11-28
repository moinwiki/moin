# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.highlight
"""

import time

import pytest

from moin.converters.highlight import Converter
from moin.utils.tree import html, moin_page


def make_tree(*texts):
    return moin_page.body(children=[moin_page.p(children=[text]) for text in texts])


def highlighted(tree):
    return [elem[0] for elem in tree.iter(moin_page.strong) if elem.get(html.class_) == "moin-highlight"]


@pytest.mark.parametrize(
    "regex,text,expected",
    [
        # plain search words are matched case-insensitively
        ("hello", "Hello world, hello!", ["Hello", "hello"]),
        ("hello world", "hello big world", ["hello", "world"]),
        # plain search words are matched literally, not as regex
        ("a.c", "abc a.c", ["a.c"]),
        ("(a+)+$", "aaaa (a+)+$", ["(a+)+$"]),
        ("[[[", "x [[[ y", ["[[["]),
        # extra whitespace does not add empty alternatives
        ("  foo   bar  ", "foo and bar", ["foo", "bar"]),
        ("", "some text", []),
        # Whoosh regex search term is used as regex, case-sensitively
        ('r"^Moin"', "MoinMoin moin", ["Moin"]),
        ('r"b+"', "abbbc b", ["bbb", "b"]),
        # zero-length matches are not highlighted
        ('r"x*"', "abc", []),
        # invalid regex highlights nothing
        ('r"[[["', "x [[[ y", []),
    ],
)
def test_highlight(regex, text, expected):
    tree = Converter(regex)(make_tree(text))
    assert highlighted(tree) == expected
    assert "".join(tree.itertext()) == text


def test_highlight_catastrophic_regex_is_aborted():
    # (a|a)+$ needs exponential time to fail on a long run of "a" not followed by end of text
    texts = ["a" * 40 + "!"] * 5
    conv = Converter('r"(a|a)+$"', timeout=0.2)
    t0 = time.monotonic()
    tree = conv(make_tree(*texts))
    # the time budget is for the whole document, not for each text node
    assert time.monotonic() - t0 < 2.0
    assert highlighted(tree) == []
    assert "".join(tree.itertext()) == "".join(texts)


def test_highlight_keeps_highlights_done_before_timeout():
    conv = Converter('r"ok|(a|a)+$"', timeout=0.2)
    tree = conv(make_tree("ok", "a" * 40 + "!", "ok"))
    assert highlighted(tree) == ["ok"]
