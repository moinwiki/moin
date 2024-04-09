# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqla store tests
"""


import pytest

from ..sqla import BytesStore, FileStore

pytest.importorskip("moin.storage.stores.sqla")  # noqa


@pytest.mark.parametrize("Store", [BytesStore, FileStore])
def test_create_and_destroy(tmpdir, Store):
    dbfile = tmpdir.join("store.sqlite")
    assert not dbfile.check()
    store = Store(f"sqlite:///{dbfile!s}")
    assert not dbfile.check()
    store.create()
    assert dbfile.check()
    store.destroy()
    # TODO: check for dropped table


@pytest.mark.parametrize("Store", [BytesStore, FileStore])
def test_from_uri(tmpdir, Store):
    store = Store.from_uri("sqlite://%s::test_base" % tmpdir)
    assert store.db_uri == "sqlite://%s" % tmpdir
    assert store.table_name == "test_base"
