# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - store wrappers
"""


from __future__ import absolute_import, division

from io import BytesIO
from collections import MutableMapping


class ByteToStreamWrappingStore(MutableMapping):
    def __init__(self, stream_store):
        """
        Wrap a file store so it can be used like a byte store.

        :param stream_store: the file/stream store to wrap
        """
        self._st = stream_store

    def __iter__(self):
        return iter(self._st)

    def __setitem__(self, key, value):
        self._st[key] = BytesIO(value)

    def __getitem__(self, key):
        return self._st[key].read()

    def __delitem__(self, key):
        del self._st[key]

    def __len__(self):
        return len(self._st)
