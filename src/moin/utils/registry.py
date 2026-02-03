# Copyright: 2008-2010 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - generic registry base class.

Each registration consists of a factory function together with a list of
arbitrary arguments. Registered entries can be ordered by priority.
During lookup, each factory is called with the provided arguments and
may return a callable to indicate a match.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Protocol, TypeAlias, TypeVar

T = TypeVar("T", covariant=True)

TFactory: TypeAlias = Callable[..., T]


class _RegistryEntry(Protocol[T]):

    @property
    def factory(self) -> TFactory: ...

    def __call__(self, *args: Any, **kw: Any) -> T | None: ...

    def __lt__(self, other: Any) -> Any: ...


class RegistryBase(Generic[T]):

    PRIORITY_REALLY_FIRST = -20
    PRIORITY_FIRST = -10
    PRIORITY_MIDDLE = 0
    PRIORITY_LAST = 10
    PRIORITY_REALLY_LAST = 20

    def __init__(self) -> None:
        self._entries: list[_RegistryEntry[T]] = []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._entries!r}>"

    def get(self, *args: Any, **kwargs: Any) -> T | None:
        """
        Look up a matching module.

        Each registered factory is called with the given arguments, and
        the first match wins.
        """
        for entry in self._entries:
            if (conv := entry(*args, **kwargs)) is not None:
                return conv
        return None

    def _register(self, entry: _RegistryEntry[T]) -> None:
        if entry not in self._entries:
            entries = self._entries[:]
            for i in range(len(entries)):
                if entry < entries[i]:
                    entries.insert(i, entry)
                    break
            else:
                entries.append(entry)
            self._entries = entries

    def unregister(self, factory: TFactory) -> None:
        """
        Unregister a factory.

        :param factory: Factory to unregister.
        """
        old_entries = self._entries
        entries = [i for i in old_entries if i.factory is not factory]
        if len(old_entries) == len(entries):
            # TODO: Is this necessary?
            raise ValueError
        self._entries = entries
