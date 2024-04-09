# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend that ties together 2 key/value stores

A meta store (a ByteStore):

- key = revid UUID (bytes, ascii)
- value = bytes (bytes, utf-8)

A data store (a FileStore):

- key = dataid UUID (bytes, ascii)
- value = file (gets/returns open file instances, to read/write binary data)

See the stores package for already implemented key/value stores.
"""

import json

from moin.constants.keys import REVID, DATAID, SIZE, HASH_ALGORITHM
from moin.utils.crypto import make_uuid

from . import BackendBase, MutableBackendBase
from ._util import TrackingFileWrapper

STORES_PACKAGE = "moin.storage.stores"


class Backend(BackendBase):
    """
    ties together a store for metadata and a store for data, readonly
    """

    @classmethod
    def from_uri(cls, uri):
        store_name_uri = uri.split(":", 1)
        if len(store_name_uri) != 2:
            raise ValueError(f"malformed store uri: {uri}")
        store_name, store_uri = store_name_uri
        module = __import__(STORES_PACKAGE + "." + store_name, globals(), locals(), ["BytesStore", "FileStore"])
        meta_store_uri = store_uri % dict(kind="meta")
        data_store_uri = store_uri % dict(kind="data")
        return cls(module.BytesStore.from_uri(meta_store_uri), module.FileStore.from_uri(data_store_uri))

    def __init__(self, meta_store, data_store):
        """
        :param meta_store: a ByteStore for metadata
        :param data_store: a FileStore for data
        """
        self.meta_store = meta_store
        self.data_store = data_store

    def open(self):
        self.meta_store.open()
        self.data_store.open()

    def close(self):
        self.meta_store.close()
        self.data_store.close()

    def __iter__(self):
        yield from self.meta_store

    def _deserialize(self, meta_str):
        text = meta_str.decode("utf-8")
        meta = json.loads(text)
        return meta

    def _get_meta(self, metaid):
        meta = self.meta_store[metaid]
        # XXX Idea: we could check the type we get from the store:
        # if it is a str/bytes, just use it "as is",
        # if it is a file, read and close it (so we have a str/bytes).
        return self._deserialize(meta)

    def _get_data(self, dataid):
        data = self.data_store[dataid]
        # XXX Idea: we could check the type we get from the store:
        # if it is a file, just return it "as is",
        # if it is a str/bytes, wrap it into BytesIO (so we always return
        # a file-like object).
        return data

    def retrieve(self, metaid):
        meta = self._get_meta(metaid)
        dataid = meta[DATAID]
        data = self._get_data(dataid)
        return meta, data


class MutableBackend(Backend, MutableBackendBase):
    """
    same as Backend, but read/write
    """

    def create(self):
        self.meta_store.create()
        self.data_store.create()

    def destroy(self):
        self.meta_store.destroy()
        self.data_store.destroy()

    def _serialize(self, meta):
        text = json.dumps(meta, ensure_ascii=False)
        meta_str = text.encode("utf-8")
        return meta_str

    def _store_meta(self, meta):
        if REVID not in meta:
            # Item.clear_revision calls us with REVID already present
            meta[REVID] = make_uuid()
        metaid = meta[REVID]
        meta = self._serialize(meta)
        # XXX Idea: we could check the type the store wants from us:
        # if it is a str/bytes (BytesStore), just use meta "as is",
        # if it is a file (FileStore), wrap it into BytesIO and give that to the store.
        self.meta_store[metaid] = meta
        return metaid

    def store(self, meta, data):
        # XXX Idea: we could check the type the store wants from us:
        # if it is a str/bytes (BytesStore), just use meta "as is",
        # if it is a file (FileStore), wrap it into BytesIO and give that to the store.
        if DATAID not in meta:
            tfw = TrackingFileWrapper(data, hash_method=HASH_ALGORITHM)
            dataid = make_uuid()
            self.data_store[dataid] = tfw
            meta[DATAID] = dataid
            # check whether size and hash are consistent:
            size_expected = meta.get(SIZE)
            size_real = tfw.size
            if size_expected is not None and size_expected != size_real:
                raise ValueError(
                    "computed data size ({}) does not match data size declared in metadata ({})".format(
                        size_real, size_expected
                    )
                )
            meta[SIZE] = size_real
            hash_expected = meta.get(HASH_ALGORITHM)
            hash_real = tfw.hash.hexdigest()
            if hash_expected is not None and hash_expected != hash_real:
                raise ValueError(
                    "computed data hash ({}) does not match data hash declared in metadata ({})".format(
                        hash_real, hash_expected
                    )
                )
            meta[HASH_ALGORITHM] = hash_real
        else:
            dataid = meta[DATAID]
            # we will just asume stuff is correct if you pass it with a data id
            if dataid not in self.data_store:
                self.data_store[dataid] = data
            else:
                # this is reading the data to avoid this issue:
                # if we do not store if we already have the dataid in the store,
                # deserialization does not work as the fpos does not advance to the next record,
                # because we do not read from the source file. Remove the check?
                while data.read(64 * 1024):
                    pass
        # if something goes wrong below, the data shall be purged by a garbage collection
        metaid = self._store_meta(meta)
        return metaid

    def _del_meta(self, metaid):
        del self.meta_store[metaid]

    def _del_data(self, dataid):
        del self.data_store[dataid]

    def remove(self, metaid, destroy_data):
        meta = self._get_meta(metaid)
        dataid = meta[DATAID]
        self._del_meta(metaid)
        if destroy_data:
            self._del_data(dataid)
