# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend utilities
"""


from __future__ import absolute_import, division

import hashlib


class TrackingFileWrapper(object):
    """
    Wraps a file and computes hashcode and file size while it is read.
    Requires that initially the realfile is open and at pos 0.
    Users need to call .read(blocksize) until it does not return any more data.
    After this self.hash and self.size will have the wanted values.
    self.hash is the hash instance, you may want to call self.hash.hexdigest().
    """
    def __init__(self, realfile, hash_method='sha1'):
        self._realfile = realfile
        self._read = realfile.read
        self._hash = hashlib.new(hash_method)
        self._size = 0
        self._finished = False
        fpos = realfile.tell()
        if fpos:
            raise ValueError("file needs to be at pos 0")

    def read(self, size=None):
        # XXX: workaround for werkzeug.wsgi.LimitedStream
        #      which expects None instead of -1 for "read everything"
        if size is None:
            data = self._read()
            self._finished = True
        else:
            data = self._read(size)
            if not data:
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

