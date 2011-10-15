# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - kyoto tycoon store tests
"""


from __future__ import absolute_import, division

import pytest
pytest.importorskip('MoinMoin.storage.stores.kt')


from MoinMoin._tests import test_connection
try:
    test_connection(1978)
except Exception as err:
    pytest.skip(str(err))


from ..kt import BytesStore, FileStore


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(Store):
    store = Store()
    store.create()
    return store


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(Store):
    store = Store()
    store.destroy()

