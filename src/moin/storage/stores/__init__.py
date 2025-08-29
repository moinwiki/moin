# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - simple key/value stores.

If some key/value store implementation you'd like to use is missing from this package,
you can likely implement it by adding very little and rather easy code.
"""

from abc import abstractmethod
from collections.abc import Mapping, MutableMapping
from io import BytesIO


class StoreBase(Mapping):
    """
    A simple read-only key/value store.
    """

    @classmethod
    @abstractmethod
    def from_uri(cls, uri):
        """
        Return an instance constructed from the given URI.
        """

    def __init__(self, **kw):
        """
        Lazy initialization — just remember paths, URLs, database name, etc.,
        whatever we need for open(), create(), etc.
        """

    def open(self):
        """
        Open the store; prepare it for usage.
        """

    def close(self):
        """
        Close the store; stop using it; free resources (except stored data).
        """

    @abstractmethod
    def __iter__(self):
        """
        Iterate over keys present in the store.
        """

    def __len__(self):
        return len([key for key in self])

    @abstractmethod
    def __getitem__(self, key):
        """
        Return data stored for key.
        """


class BytesStoreBase(StoreBase):
    @abstractmethod
    def __getitem__(self, key):
        """
        Return a byte string for key if it exists; otherwise raise KeyError.
        """


class FileStoreBase(StoreBase):
    @abstractmethod
    def __getitem__(self, key):
        """
        Return a file-like object for key if it exists; otherwise raise KeyError.

        Note: The caller is responsible for closing the open file we return
              after usage.
        """


class MutableStoreBase(StoreBase, MutableMapping):
    """
    A simple read/write key/value store.
    """

    def create(self):
        """
        Create an empty store.
        """

    def destroy(self):
        """
        Destroy the store (erase all stored data, remove store).
        """

    @abstractmethod
    def __setitem__(self, key, value):
        """
        Store value under key.
        """

    @abstractmethod
    def __delitem__(self, key):
        """
        Delete the key, dereference the related value in the store.
        """


class BytesMutableStoreBase(MutableStoreBase):
    @abstractmethod
    def __setitem__(self, key, value):
        """
        Store a bytestring for key.
        """


class BytesMutableStoreMixin:
    """
    Mix this into a FileMutableStore to get a BytesMutableStore, like shown here:

    class BytesStore(BytesMutableStoreMixin, FileStore, BytesMutableStoreBase):
        # That’s all; nothing more needed.
    """

    def __getitem__(self, key):
        with super().__getitem__(key) as stream:
            return stream.read()

    def __setitem__(self, key, value):
        with BytesIO(value) as stream:
            super().__setitem__(key, stream)


class FileMutableStoreBase(MutableStoreBase):
    @abstractmethod
    def __setitem__(self, key, stream):
        """
        Store a file-like object for key.

        Note: caller is responsible for giving us an open file and also for
              closing that file later. The caller must not rely on any specific
              file pointer position after we return.
        """


class FileMutableStoreMixin:
    """
    Mix this into a BytesMutableStore to get a FileMutableStore, like shown here:

    class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase)
        # That’s all; nothing more needed.
    """

    def __getitem__(self, key):
        value = super().__getitem__(key)
        return BytesIO(value)

    def __setitem__(self, key, stream):
        value = stream.read()
        super().__setitem__(key, value)
