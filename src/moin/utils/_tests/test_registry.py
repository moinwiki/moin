# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.utils.registry
"""


import pytest

from moin.utils.registry import Registry


def factory_all(arg):
    return 1


def factory_all2(arg):
    return 3


def factory_none(arg):
    pass


def factory_special(arg):
    if arg == "a":
        return 2


def test_Registry_get():
    r = Registry()

    r.register(factory_none)
    r.register(factory_special)
    assert r.get("a") == 2

    r.register(factory_all)
    assert r.get(None) == 1
    assert r.get("a") == 2

    r.register(factory_all2, r.PRIORITY_FIRST)
    assert r.get(None) == 3
    assert r.get("a") == 3


def test_Registry_lifecycle():
    r = Registry()

    assert len(r._entries) == 0

    r.register(factory_all)
    assert len(r._entries) == 1

    r.register(factory_none)
    assert len(r._entries) == 2

    r.register(factory_none)
    assert len(r._entries) == 2
    assert r._entries[0].factory is factory_all
    assert r._entries[1].factory is factory_none

    r.register(factory_none, r.PRIORITY_FIRST)
    assert len(r._entries) == 3
    assert r._entries[0].factory is factory_none
    assert r._entries[0].priority == r.PRIORITY_FIRST
    assert r._entries[1].factory is factory_all
    assert r._entries[2].factory is factory_none
    assert r._entries[2].priority == r.PRIORITY_MIDDLE

    r.unregister(factory_none)
    assert len(r._entries) == 1
    assert r._entries[0].factory is factory_all

    r.unregister(factory_all)
    assert len(r._entries) == 0

    pytest.raises(ValueError, r.unregister, factory_none)
    assert len(r._entries) == 0
