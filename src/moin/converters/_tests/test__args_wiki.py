# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters._args_wiki
"""

import pytest

from moin.converters._args_wiki import Arguments, parse, unparse, include_re, object_re


@pytest.mark.parametrize(
    "wiki,positional,keyword",
    [
        (r"both positional both=foo keyword=bar", ["both", "positional"], {"both": "foo", "keyword": "bar"}),
        (r"a-b a_b a-c=foo a_c=bar", ["a-b", "a_b"], {"a-c": "foo", "a_c": "bar"}),
        (r'''"a b\tc\nd" k="a b\tc\nd"''', ["a b\tc\nd"], {"k": "a b\tc\nd"}),
    ],
)
def test(wiki, positional, keyword):
    a = parse(wiki)
    assert a.positional == positional
    assert a.keyword == keyword

    s = unparse(Arguments(positional, keyword))
    assert s == wiki


def test_parse():
    a = parse(r''''a b\tc\nd',k="a b\tc\nd"''')
    assert a.positional == ["a b\tc\nd"]
    assert a.keyword == {"k": "a b\tc\nd"}


def test_include_re():
    a = parse(r''''^User/Prefix,,to="^----",sort=descending,items=3"''', parse_re=include_re)
    assert a.positional == ["^User/Prefix"]
    assert a.keyword == {"to": "^----", "sort": "descending", "items": "3"}


def test_object_re():
    a = parse(r''''width=100% height="100%"''', parse_re=object_re)
    assert a.positional == []
    assert a.keyword == {"width": "100%", "height": "100%"}
