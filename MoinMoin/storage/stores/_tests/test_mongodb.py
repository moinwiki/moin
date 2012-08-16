# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2012 Ionut Artarisi <ionut@artarisi.eu>
# Copyright: 2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - mongodb store tests
"""

import pytest
pytest.importorskip('MoinMoin.storage.stores.mongodb')
from ..mongodb import BytesStore, FileStore

from MoinMoin._tests import check_connection
try:
    check_connection(27017)
except Exception as err:
    pytest.skip(str(err))


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(Store):
    store = Store()
    store.create()
    return store

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(Store):
    store = Store()
    store.destroy()

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_from_uri(Store):
    store = Store.from_uri("mongodb://localhost/test_base::test_coll")
    assert store.uri == 'mongodb://localhost/test_base'
    assert store.collection_name == 'test_coll'
