# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - filesystem store

Store into filesystem, one file per k/v pair.
"""


from __future__ import absolute_import, division

import os
import errno
import shutil

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase


class _Store(MutableStoreBase):
    """
    A simple filesystem-based store.

    keys are required to be valid filenames.
    """
    @classmethod
    def from_uri(cls, uri):
        return cls(uri)

    def __init__(self, path):
        """
        :param path: base directory used for this store
        """
        self.path = path

    def create(self):
        os.mkdir(self.path)

    def destroy(self):
        shutil.rmtree(self.path)

    def _mkpath(self, key):
        # XXX unsafe keys?
        return os.path.join(self.path, key)

    def __iter__(self):
        for key in os.listdir(self.path):
            yield key

    def __delitem__(self, key):
        os.remove(self._mkpath(key))


class BytesStore(_Store, BytesMutableStoreBase):
    def __getitem__(self, key):
        try:
            with open(self._mkpath(key), 'rb') as f:
                return f.read() # better use get_file() and read smaller blocks for big files
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise KeyError(key)
            raise

    def __setitem__(self, key, value):
        with open(self._mkpath(key), "wb") as f:
            f.write(value)


class FileStore(_Store, FileMutableStoreBase):
    def __getitem__(self, key):
        try:
            return open(self._mkpath(key), 'rb')
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise KeyError(key)
            raise

    def __setitem__(self, key, stream):
        with open(self._mkpath(key), "wb") as f:
            blocksize = 64 * 1024
            shutil.copyfileobj(stream, f, blocksize)

