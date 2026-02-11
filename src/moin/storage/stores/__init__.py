# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - simple key/value stores.

If some key/value store implementation you'd like to use is missing from this package,
you can likely implement it by adding very little and rather easy code.
"""

from __future__ import annotations

from typing import BinaryIO, Iterator, TypeAlias, TypeVar
from typing_extensions import Self

from abc import abstractmethod
from collections.abc import MutableMapping

BinaryData = bytes | bytearray | memoryview


_StoreValueT = TypeVar("_StoreValueT")


class StoreBase(MutableMapping[str, _StoreValueT]):
    """
    A simple read/write key/value store.
    """

    @classmethod
    @abstractmethod
    def from_uri(cls: type[Self], uri: str) -> Self:
        """
        Return an instance constructed from the given URI.
        """

    def __init__(self, **kw):
        """
        Lazy initialization — just remember paths, URLs, database name, etc.,
        whatever we need for open(), create(), etc.
        """

    def create(self) -> None:
        """
        Create an empty store.
        """

    def destroy(self) -> None:
        """
        Destroy the store (erase all stored data, remove store).
        """

    def open(self) -> None:
        """
        Open the store; prepare it for usage.
        """

    def close(self) -> None:
        """
        Close the store; stop using it; free resources (except stored data).
        """

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        Iterate over keys present in the store.
        """

    def __len__(self) -> int:
        return len([key for key in self])

    @abstractmethod
    def __getitem__(self, key: str) -> _StoreValueT:
        """
        Return data stored for key.
        """
        raise KeyError

    @abstractmethod
    def __setitem__(self, key: str, value: _StoreValueT) -> None:
        """
        Store value under key.
        """
        raise KeyError

    @abstractmethod
    def __delitem__(self, key: str) -> None:
        """
        Delete the key, dereference the related value in the store.
        """
        raise KeyError


BytesStoreBase: TypeAlias = StoreBase[BinaryData]
"""
A store dealing with binary data.
"""


FileStoreBase: TypeAlias = StoreBase[BinaryIO]
"""
A store dealing with file-like objects.

Note: The caller is responsible for closing the opened files.
"""
