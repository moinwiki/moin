# Copyright: 2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.mime tests.
"""

import pytest

from moin.utils.mime import Type, get_charset


def test_Type_init_1():
    t = Type(type="foo", subtype="bar", parameters={"foo": "bar"})
    assert t.type == "foo"
    assert t.subtype == "bar"
    assert t.parameters == {"foo": "bar"}


def test_Type_init_2():
    i = "text/plain;encoding=utf-8"
    t = Type(i, type="foo", subtype="bar", parameters={"foo": "bar"})
    assert t.type == "foo"
    assert t.subtype == "bar"
    assert t.parameters == {"encoding": "utf-8", "foo": "bar"}


def test_Type_init_3():
    i = Type(type="foo", subtype="bar")
    t = Type(i)
    assert i is not t
    assert i == t
    assert i.parameters is not t.parameters


def test_Type_text():
    i = "*/*"
    t = Type(i)
    assert t.type == ""
    assert t.subtype == ""
    assert t.parameters == {}
    assert str(t) == i

    i = "text/*"
    t = Type(i)
    assert t.type == "text"
    assert t.subtype == ""
    assert t.parameters == {}
    assert str(t) == i

    i = "text/plain"
    t = Type(i)
    assert t.type == "text"
    assert t.subtype == "plain"
    assert t.parameters == {}
    assert str(t) == i

    i = "text/plain;encoding=utf-8;foo=bar"
    t = Type(i)
    assert t.type == "text"
    assert t.subtype == "plain"
    assert t.parameters == {"encoding": "utf-8", "foo": "bar"}
    assert str(t) == i

    i = 'text/plain;encoding=utf-8;foo="["'
    t = Type(i)
    assert t.parameters == {"encoding": "utf-8", "foo": "["}
    assert str(t) == i


def test_Type_compare():
    t1 = Type(type="text", subtype="plain")

    assert t1 == t1
    assert t1.issupertype(t1)

    t2 = Type(type="text")
    assert t1 != t2
    assert t2.issupertype(t1)
    assert not t1.issupertype(t2)

    t2 = Type(type="text", subtype="plain", parameters={"encoding": "iso8859-1"})
    assert t1 != t2
    assert t1.issupertype(t2)
    assert not t2.issupertype(t1)

    t3 = Type(type="text", subtype="plain", parameters={"encoding": "utf-8"})
    assert t2 != t3
    assert not t2.issupertype(t3)
    assert not t3.issupertype(t2)

    t2 = Type(type="text", subtype="html")
    assert t1 != t2
    assert not t1.issupertype(t2)
    assert not t2.issupertype(t1)


@pytest.mark.parametrize(
    "contenttype,expected",
    [
        ("text/x.moin.wiki;charset=utf-8", "utf-8"),
        ('text/plain;charset="utf-8"', "utf-8"),  # quoted, as created by MimeType.content_type()
        ('text/plain; charset="UTF-8"', "UTF-8"),  # whitespace
        ("text/x.moin.wiki;charset=utf-8;format=1.9", "utf-8"),  # additional parameter
        ("text/x.moin.wiki;format=1.9;charset=ascii", "ascii"),  # charset not the last parameter
        ("text/plain", "utf-8"),  # no charset -> default
    ],
)
def test_get_charset(contenttype, expected):
    assert get_charset(contenttype) == expected


def test_get_charset_default():
    assert get_charset("text/plain", default="ascii") == "ascii"
