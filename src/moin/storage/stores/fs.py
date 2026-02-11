# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - filesystem store.

Store in the file system, one file per key/value pair.
"""

from __future__ import annotations

from typing import BinaryIO, Iterator
from typing_extensions import Self

import os
import errno
import shutil

from io import BytesIO

from . import BinaryData, BytesStoreBase, FileStoreBase


class FileStoreMixin:

    @classmethod
    def from_uri(cls: type[Self], uri: str) -> Self:
        return cls(uri)

    def __init__(self, path: str) -> None:
        """
        :param path: Base directory used for this store.
        """
        self.path = path

    def create(self) -> None:
        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def destroy(self) -> None:
        shutil.rmtree(self.path)

    def _mkpath(self, key: str) -> str:
        return os.path.join(self.path, key)

    def __iter__(self) -> Iterator[str]:
        yield from os.listdir(self.path)

    def __delitem__(self, key: str) -> None:
        os.remove(self._mkpath(key))

    def _getitem(self, key: str) -> BinaryIO:
        try:
            return open(self._mkpath(key), "rb")
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise KeyError(key)
            raise

    def _setitem(self, key: str, stream: BinaryIO) -> None:
        with open(self._mkpath(key), "wb") as f:
            blocksize = 64 * 1024
            shutil.copyfileobj(stream, f, blocksize)


class FileStore(FileStoreMixin, FileStoreBase):
    """
    A simple filesystem-based store.

    Keys are required to be valid filenames.
    """

    def __getitem__(self, key: str) -> BinaryIO:
        return self._getitem(key)

    def __setitem__(self, key: str, stream: BinaryIO) -> None:
        self._setitem(key, stream)


class BytesStore(FileStoreMixin, BytesStoreBase):
    """
    Filesystem BytesStore.
    """

    def __getitem__(self, key: str) -> BinaryData:
        with self._getitem(key) as stream:
            return stream.read()

    def __setitem__(self, key: str, value: BinaryData) -> None:
        with BytesIO(value) as stream:
            self._setitem(key, stream)
