# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - kyoto tycoon store tests
"""


from __future__ import absolute_import, division

import pytest
pytest.importorskip('storage.stores.kt')

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

