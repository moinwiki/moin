# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters._args
"""


import pytest

from moin.converters._args import Arguments


def test_Arguments___init__():
    positional = []
    keyword = {}

    a = Arguments(positional, keyword)

    assert positional == a.positional
    assert positional is not a.positional
    assert keyword == a.keyword
    assert keyword is not a.keyword


def test_Arguments___contains__():
    positional = ["positional", "both"]
    keyword = {"keyword": None, "both": None}

    a = Arguments(positional, keyword)

    assert "positional" in a
    assert "keyword" in a
    assert "both" in a
    assert "none" not in a


def test_Arguments___getitem__():
    positional = ["positional", "both"]
    keyword = {"keyword": None, "both": None}

    a = Arguments(positional, keyword)

    assert a[0] == "positional"
    assert a[1] == "both"
    assert a[:] == positional
    assert a["keyword"] is None
    assert a["both"] is None

    pytest.raises(IndexError, a.__getitem__, 2)
    pytest.raises(KeyError, a.__getitem__, "none")


def test_Arguments___len__():
    positional = ["positional", "both"]
    keyword = {"keyword": None, "both": None}

    a = Arguments(positional, keyword)

    assert len(a) == 4


def test_Arguments_items():
    positional = ["positional", "both"]
    keyword = {"keyword": True, "both": False}

    a = Arguments(positional, keyword)

    args = list(a.items())

    assert len(args) == 4
    assert args[0] == (None, "positional")
    assert args[1] == (None, "both")
    assert ("keyword", True) in args
    assert ("both", False) in args


def test_Arguments_keys():
    positional = ["positional", "both"]
    keyword = {"keyword": True, "both": False}

    a = Arguments(positional, keyword)

    args = list(a.keys())

    assert len(args) == 2
    assert "keyword" in args
    assert "both" in args


def test_Arguments_values():
    positional = ["positional", "both"]
    keyword = {"keyword": True, "both": False}

    a = Arguments(positional, keyword)

    args = list(a.values())

    assert len(args) == 4
    assert args[0] == "positional"
    assert args[1] == "both"
    assert True in args
    assert False in args
