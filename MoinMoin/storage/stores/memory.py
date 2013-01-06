# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - memory store

Stores k/v pairs into memory (RAM, non-persistent!).

Note: likely this is mostly useful for unit tests.
"""


from __future__ import absolute_import, division

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase, StringIO


class _Store(MutableStoreBase):
    """
    A simple dict-based in-memory store. No persistence!
    """
    @classmethod
    def from_uri(cls, uri):
        return cls()

    def __init__(self):
        self._st = None
        self.__st = None

    def create(self):
        self.__st = {}

    def destroy(self):
        self.__st = None

    def open(self):
        self._st = self.__st

    def close(self):
        self._st = None

    def __iter__(self):
        for key in self._st:
            yield key

    def __delitem__(self, key):
        del self._st[key]


class BytesStore(_Store, BytesMutableStoreBase):
    def __getitem__(self, key):
        return self._st[key]

    def __setitem__(self, key, value):
        self._st[key] = value


class FileStore(_Store, FileMutableStoreBase):
    def __getitem__(self, key):
        return StringIO(self._st[key])

    def __setitem__(self, key, stream):
        self._st[key] = stream.read()
