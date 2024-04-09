# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlite store tests
"""


import pytest

from ..sqlite import BytesStore, FileStore


def bytes_compressed(path):
    return BytesStore(path, "test_table", compression_level=1)


def bytes_uncompressed(path):
    return BytesStore(path, "test_table", compression_level=0)


def file_compressed(path):
    return FileStore(path, "test_table", compression_level=1)


def file_uncompressed(path):
    return FileStore(path, "test_table", compression_level=0)


all_setups = pytest.mark.parametrize(
    "Store", [bytes_uncompressed, bytes_compressed, file_uncompressed, file_compressed]
)


@all_setups
def test_create(tmpdir, Store):
    dbfile = tmpdir.join("store.sqlite")
    assert not dbfile.check()
    store = Store(str(dbfile))
    assert not dbfile.check()
    store.create()
    assert dbfile.check()
    store.destroy()
    # TODO: check for dropped table


@pytest.mark.parametrize("Store", [BytesStore, FileStore])
def test_from_uri(tmpdir, Store):
    store = Store.from_uri("%s::test_table::0" % tmpdir)
    assert store.db_name == tmpdir
    assert store.table_name == "test_table"
    assert store.compression_level == 0

    store = Store.from_uri("%s::test_table::2" % tmpdir)
    assert store.db_name == tmpdir
    assert store.table_name == "test_table"
    assert store.compression_level == 2
