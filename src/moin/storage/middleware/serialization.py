# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend serialization / deserialization

We use a simple custom format here::

    4 bytes length of meta (m)
    m bytes metadata (json serialization, utf-8 encoded)
            (the metadata contains the data length d in meta[SIZE])
    d bytes binary data
    ... (repeat for all meta/data)
    4 bytes 00 (== length of next meta -> there is none, this is the end)
"""

import struct
import json

from werkzeug.wsgi import LimitedStream

from moin.constants.keys import NAME, ITEMTYPE, SIZE, NAMESPACE, REVID, ITEMID, REV_NUMBER, HASH_ALGORITHM
from moin.constants.itemtypes import ITEMTYPE_DEFAULT
from moin.storage.backends.stores import Backend
from moin.storage.backends._util import TrackingFileWrapper

from moin import log

logging = log.getLogger(__name__)


def serialize(backend, dst):
    dst.writelines(serialize_iter(backend))


def serialize_rev(meta, data):
    if meta is None:
        # this is the end!
        yield struct.pack("!i", 0)
    else:
        text = json.dumps(meta, ensure_ascii=False)
        meta_str = text.encode("utf-8")
        yield struct.pack("!i", len(meta_str))
        yield meta_str
        while True:
            block = data.read(8192)
            if not block:
                break
            yield block


def get_rev_str(meta):
    """return string representing a revision for use in logging"""
    ns = meta.get(NAMESPACE)
    name = None
    names = meta.get(NAME)
    if names:
        name = names[0]
    return (
        f'name: {ns + "/" if ns else ""}{name} item: {meta.get(ITEMID)} rev_number: {meta.get(REV_NUMBER)} '
        f"rev_id: {meta.get(REVID)}"
    )


def correcting_rev_iter(backend: Backend):
    """iterate over the revisions in a store yielding corrected metadata
    yields tuples of meta, data, issues
        meta: dict of metadata with corrected size and sha1
        data: the item data
        issues: list of str messages describing issues which were corrected"""
    for revid in backend:
        issues = []
        if isinstance(revid, tuple):
            # router middleware gives tuples and wants both values for retrieve:
            meta, data = backend.retrieve(*revid)
        else:
            # lower level backends have simple revids
            meta, data = backend.retrieve(revid)
        tfw = TrackingFileWrapper(data)
        while tfw.read(64 * 1024):
            pass
        if tfw.size != meta[SIZE]:
            issues.append(f"{SIZE}_error {get_rev_str(meta)} meta_size: {meta[SIZE]} real_size: {tfw.size}")
            meta[SIZE] = tfw.size
        if (real_hash := tfw.hash.hexdigest()) != meta[HASH_ALGORITHM]:
            issues.append(
                f"{HASH_ALGORITHM}_error {get_rev_str(meta)} meta_{HASH_ALGORITHM}: {meta[HASH_ALGORITHM]} "
                f"real_{HASH_ALGORITHM}: {real_hash}"
            )
            meta[HASH_ALGORITHM] = real_hash
        data.seek(0)
        yield meta, data, issues


def serialize_iter(backend):
    issues_found = False
    for meta, data, issues in correcting_rev_iter(backend):
        if issues:
            issues_found = True
            for issue in issues:
                logging.info(issue)
        yield from serialize_rev(meta, data)
    for data in serialize_rev(None, None):
        yield data
    if issues_found:
        logging.warning("metadata issues exist! maint-validate-metadata followed by index rebuild is recommended")


def deserialize(src, backend, new_ns=None, old_ns=None, kill_ns=None):
    """
    Normal usage is to restore an empty wiki with data from a backup.

    If new_ns and old_ns are passed, then all items in the old_ns are renamed into the new_ns.
    If kill_ns is passed, then all items in that namespace are not loaded.
    """
    assert bool(new_ns is None) == bool(old_ns is None), "new_ns and old_ns are co-dependent options"
    while True:
        meta_size_bytes = src.read(4)
        if not len(meta_size_bytes):
            return  # end of file
        meta_size = struct.unpack("!i", meta_size_bytes)[0]
        if not meta_size:
            continue  # end of store
        meta_str = src.read(meta_size)
        text = meta_str.decode("utf-8")
        meta = json.loads(text)
        name = meta.get(NAME)
        if isinstance(name, str):
            # if we encounter single names, make a list of names:
            meta[NAME] = [name]
        if ITEMTYPE not in meta:
            # temporary hack to upgrade serialized item files:
            meta[ITEMTYPE] = ITEMTYPE_DEFAULT
        data_size = meta[SIZE]
        curr_pos = src.tell()
        limited = LimitedStream(src, data_size)

        if kill_ns and kill_ns == meta[NAMESPACE]:
            continue
        if new_ns is not None and old_ns == meta[NAMESPACE]:
            meta[NAMESPACE] = new_ns

        backend.store(meta, limited)
        if not limited.is_exhausted:
            # if we already have the DATAID in the backend, the backend code
            # does not read from the limited stream:
            assert limited._pos == 0
            # but we must seek to get forward to the next item:
            src.seek(curr_pos + data_size)
