# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - simple key/value stores.

If some kvstore implementation you'ld like to use is missing from this package,
you can likely implement it adding very little and rather easy code.
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
        return an instance constructed from the given uri
        """

    def __init__(self, **kw):
        """
        lazy stuff - just remember pathes, urls, database name, ... -
        whatever we need for open(), create(), etc.
        """

    def open(self):
        """
        open the store, prepare it for usage
        """

    def close(self):
        """
        close the store, stop using it, free resources (except stored data)
        """

    @abstractmethod
    def __iter__(self):
        """
        iterate over keys present in the store
        """

    def __len__(self):
        return len([key for key in self])

    @abstractmethod
    def __getitem__(self, key):
        """
        return data stored for key
        """


class BytesStoreBase(StoreBase):
    @abstractmethod
    def __getitem__(self, key):
        """
        return bytestring for key if exists else raise KeyError
        """


class FileStoreBase(StoreBase):
    @abstractmethod
    def __getitem__(self, key):
        """
        return a filelike for key if exists else raise KeyError

        note: the caller is responsible for closing the open file we return
              after usage.
        """


class MutableStoreBase(StoreBase, MutableMapping):
    """
    A simple read/write key/value store.
    """

    def create(self):
        """
        create an empty store
        """

    def destroy(self):
        """
        destroy the store (erase all stored data, remove store)
        """

    @abstractmethod
    def __setitem__(self, key, value):
        """
        store value under key
        """

    @abstractmethod
    def __delitem__(self, key):
        """
        delete the key, dereference the related value in the store
        """


class BytesMutableStoreBase(MutableStoreBase):
    @abstractmethod
    def __setitem__(self, key, value):
        """
        store a bytestring for key
        """


class BytesMutableStoreMixin:
    """
    mix this into a FileMutableStore to get a BytesMutableStore, like shown here:

    class BytesStore(BytesMutableStoreMixin, FileStore, BytesMutableStoreBase):
        # that's all, nothing more needed
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
        store a filelike for key

        note: caller is responsible for giving us a open file AND also for
              closing that file later. caller must not rely on some specific
              file pointer position after we return.
        """


class FileMutableStoreMixin:
    """
    mix this into a BytesMutableStore to get a FileMutableStore, like shown here:

    class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase)
        # that's all, nothing more needed
    """

    def __getitem__(self, key):
        value = super().__getitem__(key)
        return BytesIO(value)

    def __setitem__(self, key, stream):
        value = stream.read()
        super().__setitem__(key, value)
