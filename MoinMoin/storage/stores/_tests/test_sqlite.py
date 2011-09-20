# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlite store tests
"""


import pytest

from ..sqlite import BytesStore, FileStore

def bytes_compressed(path):
    return BytesStore(path, 'test_table', compression_level=1)
def bytes_uncompressed(path):
    return BytesStore(path, 'test_table', compression_level=0)

def file_compressed(path):
    return FileStore(path, 'test_table', compression_level=1)
def file_uncompressed(path):
    return FileStore(path, 'test_table', compression_level=0)

all_setups = pytest.mark.multi(Store=[
    bytes_uncompressed,
    bytes_compressed,
    file_uncompressed,
    file_compressed,
])


@all_setups
def test_create(tmpdir, Store):
    dbfile = tmpdir.join('store.sqlite')
    assert not dbfile.check()
    store = Store(str(dbfile))
    assert not dbfile.check()
    store.create()
    assert dbfile.check()
    return store

@all_setups
def test_destroy(tmpdir, Store):
    dbfile = tmpdir.join('store.sqlite')
    store = test_create(tmpdir, Store)
    store.destroy()
    # XXX: check for dropped table

