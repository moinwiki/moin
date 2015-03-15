# Copyright: 2012 Ionut Artarisi <ionut@artarisi.eu>
# Copyright: 2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - mongodb store

Stores k/v pairs into a MongoDB server using pymongo.
"""

from __future__ import absolute_import, division

import pymongo
import gridfs

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase


class _Store(MutableStoreBase):
    """
    MongoDB based store.
    """
    @classmethod
    def from_uri(cls, uri):
        params = uri.split('::')  # moin_uri -> mongodb_uri::collection_name
        return cls(*params)

    def __init__(self, uri='mongodb://127.0.0.1/moin_db', collection_name='moin_coll'):
        """
        Store params for .open().

        :param uri: MongoDB server uri
        """
        self.uri = uri
        self.dbname = uri.rsplit('/', 1)[-1]
        self.collection_name = collection_name

    def create(self):
        pass

    def open(self):
        self.conn = pymongo.Connection(self.uri)
        self.db = self.conn[self.dbname]
        self.coll = self.db[self.collection_name]

    def close(self):
        self.conn.close()


class BytesStore(_Store, BytesMutableStoreBase):
    def destroy(self):
        self.open()
        self.db.drop_collection(self.coll)
        self.close()

    def __getitem__(self, key):
        d = self.coll.find_one(dict(key=key))
        if d is None:
            raise KeyError(key)
        return d['value']

    def __setitem__(self, key, value):
        self.coll.insert(dict(key=key, value=value))

    def __delitem__(self, key):
        self.coll.remove(dict(key=key))

    def __iter__(self):
        for result in self.coll.find(fields=['key']):
            yield result['key']


class FileStore(_Store, FileMutableStoreBase):
    def open(self):
        super(FileStore, self).open()
        self.gridfs = gridfs.GridFS(self.db, self.collection_name)

    def destroy(self):
        self.open()
        self.db.drop_collection(self.coll.files)
        self.db.drop_collection(self.coll.chunks)
        self.db.drop_collection(self.coll)
        self.close()

    def __getitem__(self, key):
        try:
            value = self.gridfs.get(key)
        except gridfs.NoFile:
            raise KeyError(key)
        return value

    def __setitem__(self, key, stream):
        self.gridfs.delete(key)
        self.gridfs.put(stream, _id=key)

    def __delitem__(self, key):
        self.gridfs.delete(key)

    def __iter__(self):
        for result in self.coll.files.find(fields=['_id']):
            yield result['_id']
