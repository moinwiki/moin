# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.registry tests.
"""

from __future__ import annotations

from typing import Any, cast, Callable, NamedTuple

import pytest

from moin.utils.registry import RegistryBase


class Registry(RegistryBase[int]):

    class Entry(NamedTuple):
        factory: Callable[..., int | None]
        priority: int

        def __call__(self, *args: Any, **kwargs: Any) -> int | None:
            return self.factory(*args, **kwargs)

        def __lt__(self, other: Any):
            if isinstance(other, self.__class__):
                return self.priority < other.priority
            return NotImplemented

    def register(self, factory: Callable[..., int | None], priority: int = RegistryBase.PRIORITY_MIDDLE):
        """
        Register a factory

        :param factory: Factory to register. Callable, have to return a class
        """
        self._register(self.Entry(factory, priority))

    def at(self, index: int) -> Registry.Entry:
        return cast(Registry.Entry, self._entries[index])


def factory_all(arg: str | None) -> int:
    return 1


def factory_all2(arg: str | None) -> int:
    return 3


def factory_none(arg: str | None) -> None:
    pass


def factory_special(arg: str | None) -> int | None:
    if arg == "a":
        return 2
    return None


def test_Registry_get() -> None:
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
    assert r.at(0).factory is factory_all
    assert r.at(1).factory is factory_none

    r.register(factory_none, r.PRIORITY_FIRST)
    assert len(r._entries) == 3
    assert r.at(0).factory is factory_none
    assert r.at(0).priority == r.PRIORITY_FIRST
    assert r.at(1).factory is factory_all
    assert r.at(2).factory is factory_none
    assert r.at(2).priority == r.PRIORITY_MIDDLE

    r.unregister(factory_none)
    assert len(r._entries) == 1
    assert r.at(0).factory is factory_all

    r.unregister(factory_all)
    assert len(r._entries) == 0

    pytest.raises(ValueError, r.unregister, factory_none)
    assert len(r._entries) == 0
