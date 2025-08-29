# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend utilities.
"""

import hashlib


class TrackingFileWrapper:
    """
    Wrap a file and compute a hash and file size as it is read.

    The underlying file must be open and positioned at 0 initially.
    Call read(blocksize) repeatedly until it returns no more data.
    After that, the size and hash properties are available.
    The hash property is the hash instance; call hash.hexdigest() if needed.
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
                raise ValueError("file must be at position 0")

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
            raise AttributeError("Do not access the size attribute before having read all data")
        return self._size

    @property
    def hash(self):
        if not self._finished:
            raise AttributeError("Do not access the hash attribute before having read all data")
        return self._hash
