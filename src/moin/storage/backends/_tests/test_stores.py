# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - stores backend tests

Note: theoretically, it should be enough to test with one kind of store,
      but we better test with a fs AND a memory store.
"""

import os
import tempfile

from ..stores import MutableBackend
from . import MutableBackendTestBase

from moin.storage.stores.memory import BytesStore as MemoryBytesStore
from moin.storage.stores.memory import FileStore as MemoryFileStore
from moin.storage.stores.fs import BytesStore as FSBytesStore
from moin.storage.stores.fs import FileStore as FSFileStore
from moin.storage.stores.sqla import BytesStore as SQLABytesStore
from moin.storage.stores.sqla import FileStore as SQLAFileStore


class TestMemoryBackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_store = MemoryBytesStore()
        data_store = MemoryFileStore()
        self.be = MutableBackend(meta_store, data_store)
        self.be.create()
        self.be.open()


class TestFSBackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_path = tempfile.mkdtemp()
        os.rmdir(meta_path)
        meta_store = FSBytesStore(meta_path)
        data_path = tempfile.mkdtemp()
        os.rmdir(data_path)
        data_store = FSFileStore(data_path)
        self.be = MutableBackend(meta_store, data_store)
        self.be.create()
        self.be.open()


class TestSQLABackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_path = tempfile.mktemp()
        data_path = tempfile.mktemp()
        meta_store = SQLABytesStore(f"sqlite:///{meta_path}")
        data_store = SQLAFileStore(f"sqlite:///{data_path}")
        self.be = MutableBackend(meta_store, data_store)
        self.be.create()
        self.be.open()
