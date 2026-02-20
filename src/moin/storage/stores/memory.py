# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - memory store

Stores key/value pairs in memory (RAM, non-persistent!).

Note: likely this is mostly useful for unit tests.
"""

from typing import BinaryIO, Iterator
from typing_extensions import override, Self

from io import BytesIO
from . import BinaryData, BytesStoreBase, FileStoreBase


class MemoryStoreMixin:
    """
    A simple dict-based in-memory store. No persistence!
    """

    @classmethod
    def from_uri(cls: type[Self], uri: str) -> Self:
        return cls()

    def __init__(self) -> None:
        self._st: dict[str, BinaryData] | None = None
        self.__st: dict[str, BinaryData] | None = None

    def create(self) -> None:
        self.__st = {}

    def destroy(self) -> None:
        if self._st is not None:
            self.close()
        self.__st = None

    def open(self) -> None:
        if self.__st is None:
            raise ValueError("I/O operation on non-existing store.")
        self._st = self.__st

    def close(self) -> None:
        self._st = None

    def __iter__(self) -> Iterator:
        if self._st is None:
            raise
        yield from self._st

    def __delitem__(self, key: str) -> None:
        if self._st is None:
            raise ValueError("I/O operation on closed store.")
        del self._st[key]

    def _getitem(self, key: str) -> BinaryData:
        if self._st is None:
            raise ValueError("I/O operation on closed store.")
        return self._st[key]

    def _setitem(self, key: str, value: BinaryData) -> None:
        if self._st is None:
            raise ValueError("I/O operation on closed store.")
        self._st[key] = value


class BytesStore(MemoryStoreMixin, BytesStoreBase):
    """
    A simple dict-based in-memory store. No persistence!
    """

    @override
    def __getitem__(self, key: str) -> BinaryData:
        return self._getitem(key)

    @override
    def __setitem__(self, key: str, value: BinaryData) -> None:
        self._setitem(key, value)


class FileStore(MemoryStoreMixin, FileStoreBase):
    """
    In-memory FileStore.
    """

    @override
    def __getitem__(self, key: str) -> BinaryIO:
        value = self._getitem(key)
        return BytesIO(value)

    @override
    def __setitem__(self, key: str, stream: BinaryIO) -> None:
        value = stream.read()
        self._setitem(key, value)
