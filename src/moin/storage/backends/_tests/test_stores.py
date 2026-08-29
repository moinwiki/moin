# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - stores backend tests.

Note: Theoretically, testing one kind of store would be enough, but we test with
both a file system store and a memory store.
"""

import os
import tempfile
from io import BytesIO

from moin.storage.backends.stores import Backend
from moin.storage.stores.memory import BytesStore as MemoryBytesStore
from moin.storage.stores.memory import FileStore as MemoryFileStore
from moin.storage.stores.fs import BytesStore as FSBytesStore
from moin.storage.stores.fs import FileStore as FSFileStore
from moin.storage.stores.sqla import BytesStore as SQLABytesStore
from moin.storage.stores.sqla import FileStore as SQLAFileStore

from . import MutableBackendTestBase


class TestMemoryBackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_store = MemoryBytesStore()
        data_store = MemoryFileStore()
        self.be = Backend(meta_store, data_store)
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
        self.be = Backend(meta_store, data_store)
        self.be.create()
        self.be.open()


def test_open_creates_missing_fs_backend_directories(tmp_path):
    meta_path = tmp_path / "meta"
    data_path = tmp_path / "data"
    backend = Backend(FSBytesStore(str(meta_path)), FSFileStore(str(data_path)))

    backend.open()
    metaid = backend.store({"name": "Home"}, BytesIO(b"content"))
    _, stored_data = backend.retrieve(metaid)

    assert stored_data.read() == b"content"
    assert meta_path.is_dir()
    assert data_path.is_dir()
    stored_data.close()
    backend.close()


def test_open_read_only_fs_backend_does_not_create_missing_directories(tmp_path):
    meta_path = tmp_path / "meta"
    data_path = tmp_path / "data"
    backend = Backend(FSBytesStore(str(meta_path)), FSFileStore(str(data_path)), read_only=True)

    backend.open()

    assert not meta_path.exists()
    assert not data_path.exists()
    backend.close()


class TestSQLABackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_path = tempfile.mktemp()
        data_path = tempfile.mktemp()
        meta_store = SQLABytesStore(f"sqlite:///{meta_path}")
        data_store = SQLAFileStore(f"sqlite:///{data_path}")
        self.be = Backend(meta_store, data_store)
        self.be.create()
        self.be.open()
