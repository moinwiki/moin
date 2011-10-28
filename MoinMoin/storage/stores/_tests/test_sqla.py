# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqla store tests
"""


import pytest
pytest.importorskip('MoinMoin.storage.stores.sqla')
from ..sqla import BytesStore, FileStore

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(tmpdir, Store):
    dbfile = tmpdir.join('store.sqlite')
    assert not dbfile.check()
    store = Store('sqlite:///{0!s}'.format(dbfile))
    assert not dbfile.check()
    store.create()
    assert dbfile.check()
    return store

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(tmpdir, Store):
    dbfile = tmpdir.join('store.sqlite')
    store = test_create(tmpdir, Store)
    store.destroy()
    # XXX: check for dropped table

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_from_uri(tmpdir, Store):
    store = Store.from_uri("sqlite://%s/test_base" % tmpdir)
    assert store.db_uri == "sqlite://%s/test_base" % tmpdir
    assert store.table_name == "test_base"
