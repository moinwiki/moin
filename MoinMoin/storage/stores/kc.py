# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - kyoto cabinet store

Stores k/v pairs into a single kyoto cabinet file in the filesystem.

Note: only ONE process can open a kyoto cabinet in OWRITER (writable) mode.
      Multithreading is allowed, but not multi-process.

      For multi-process, you either need to use some different store (not
      kyoto cabinet) or use a store for kyoto tycoon (which is a network
      server that uses kyoto cabinet).
"""


from __future__ import absolute_import, division

import os, errno

from kyotocabinet import *

from . import (BytesMutableStoreBase, FileMutableStoreBase,
               BytesMutableStoreMixin, FileMutableStoreMixin)


class BytesStore(BytesMutableStoreBase):
    """
    Kyoto cabinet based store.
    """
    @classmethod
    def from_uri(cls, uri):
        return cls(uri)

    def __init__(self, path, mode=DB.OWRITER|DB.OAUTOTRAN, db_opts=DB.GCONCURRENT):
        """
        Store params for .open(). Please refer to kyotocabinet-python-legacy docs for more information.

        :param path: db path + options, examples:
                     "db.kch" - no compression, no encryption
                     "db.kch#zcomp=zlib" - ZLIB compression
                     "db.kch#zcomp=arc#zkey=yoursecretkey" - ARC4 encryption
                     "db.kch#zcomp=arcz#zkey=yoursecretkey" - ARC4 encryption, ZLIB compression
        :param mode: mode given to DB.open call (default: DB.OWRITER|DB.OAUTOTRAN)
        :param db_opts: opts given to DB(opts=...) constructor (default: DB.GCONCURRENT)
        """
        self.path = path
        self.mode = mode
        self.db_opts = db_opts

    def create(self):
        basedir = os.path.dirname(self.path)
        try:
            os.makedirs(basedir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        self.open(mode=self.mode|DB.OCREATE)
        self.close()

    def destroy(self):
        os.remove(self.path)

    def open(self, mode=None):
        self._db = DB(self.db_opts)
        if mode is None:
            mode = self.mode
        if not self._db.open(self.path, mode):
            raise IOError("open error: " + str(self._db.error()))

    def close(self):
        if not self._db.close():
            raise IOError("close error: " + str(self._db.error()))

    def __len__(self):
        return len(self._db)

    def __iter__(self):
        return iter(self._db)

    def __delitem__(self, key):
        self._db.remove(key)

    def __getitem__(self, key):
        value = self._db.get(key)
        if value is None:
            raise KeyError("get error: " + str(self._db.error()))
        return value

    def __setitem__(self, key, value):
        if not self._db.set(key, value):
            raise KeyError("set error: " + str(self._db.error()))


class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase):
    """Kyoto Cabinet FileStore"""
