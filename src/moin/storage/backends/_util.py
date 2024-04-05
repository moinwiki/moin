# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend utilities
"""

import hashlib


class TrackingFileWrapper:
    """
    Wraps a file and computes hashcode and file size while it is read.
    Requires that initially the realfile is open and at pos 0.
    Users need to call .read(blocksize) until it does not return any more data.
    After this self.hash and self.size will have the wanted values.
    self.hash is the hash instance, you may want to call self.hash.hexdigest().
    """

    def __init__(self, realfile, hash_method="sha1"):
        self._realfile = realfile
        self._read = realfile.read
        self._hash = hashlib.new(hash_method)
        self._size = 0
        self._finished = False
        if hasattr(realfile, "tell"):
            fpos = realfile.tell()
            if fpos:
                raise ValueError("file needs to be at pos 0")

    def read(self, size=-1):
        data = self._read(size)
        if not data or size == -1:
            self._finished = True
        self._hash.update(data)
        self._size += len(data)
        return data

    @property
    def size(self):
        if not self._finished:
            raise AttributeError("do not access size attribute before having read all data")
        return self._size

    @property
    def hash(self):
        if not self._finished:
            raise AttributeError("do not access hash attribute before having read all data")
        return self._hash
