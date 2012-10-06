# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - stores backend tests

Note: theoretically, it should be enough to test with one kind of store,
      but we better test with a fs AND a memory store.
"""


from __future__ import absolute_import, division

import pytest

from ..stores import MutableBackend
from . import MutableBackendTestBase

from MoinMoin.storage.stores.memory import BytesStore as MemoryBytesStore
from MoinMoin.storage.stores.memory import FileStore as MemoryFileStore

class TestMemoryBackend(MutableBackendTestBase):
    def setup_method(self, method):
        meta_store = MemoryBytesStore()
        data_store = MemoryFileStore()
        self.be = MutableBackend(meta_store, data_store)
        self.be.create()
        self.be.open()

import os
import tempfile

from MoinMoin.storage.stores.fs import BytesStore as FSBytesStore
from MoinMoin.storage.stores.fs import FileStore as FSFileStore

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
