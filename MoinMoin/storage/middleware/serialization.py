# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend serialization / deserialization

We use a simple custom format here:

4 bytes length of meta (m)
m bytes metadata (json serialization, utf-8 encoded)
        (the metadata contains the data length d in meta[SIZE])
d bytes binary data
... (repeat for all meta/data)
4 bytes 00 (== length of next meta -> there is none, this is the end)
"""


from __future__ import absolute_import, division

import struct
import json
from io import BytesIO

from werkzeug.wsgi import LimitedStream

from MoinMoin.constants.keys import NAME, ITEMTYPE, SIZE
from MoinMoin.constants.itemtypes import ITEMTYPE_DEFAULT


def serialize(backend, dst):
    dst.writelines(serialize_iter(backend))


def serialize_rev(meta, data):
    if meta is None:
        # this is the end!
        yield struct.pack('!i', 0)
    else:
        text = json.dumps(meta, ensure_ascii=False)
        meta_str = text.encode('utf-8')
        yield struct.pack('!i', len(meta_str))
        yield meta_str
        while True:
            block = data.read(8192)
            if not block:
                break
            yield block


def serialize_iter(backend):
    for revid in backend:
        if isinstance(revid, tuple):
            # router middleware gives tuples and wants both values for retrieve:
            meta, data = backend.retrieve(*revid)
        else:
            # lower level backends have simple revids
            meta, data = backend.retrieve(revid)
        for data in serialize_rev(meta, data):
            yield data
    for data in serialize_rev(None, None):
        yield data


def deserialize(src, backend):
    while True:
        meta_size_bytes = src.read(4)
        meta_size = struct.unpack('!i', meta_size_bytes)[0]
        if not meta_size:
            return
        meta_str = src.read(meta_size)
        text = meta_str.decode('utf-8')
        meta = json.loads(text)
        name = meta.get(NAME)
        if isinstance(name, unicode):
            # if we encounter single names, make a list of names:
            meta[NAME] = [name, ]
        if ITEMTYPE not in meta:
            # temporary hack to upgrade serialized item files:
            meta[ITEMTYPE] = ITEMTYPE_DEFAULT
        data_size = meta[SIZE]
        curr_pos = src.tell()
        limited = LimitedStream(src, data_size)
        backend.store(meta, limited)
        if not limited.is_exhausted:
            # if we already have the DATAID in the backend, the backend code
            # does not read from the limited stream:
            assert limited._pos == 0
            # but we must seek to get forward to the next item:
            src.seek(curr_pos + data_size)
