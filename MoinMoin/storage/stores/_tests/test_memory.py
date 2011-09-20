# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - memory store tests
"""

import pytest

from ..memory import BytesStore, FileStore


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(Store):
    store = Store()
    assert store._st is None

    store.create()
    assert store._st == {}

    return store

@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(Store):
    store = test_create(Store)
    store.destroy()
    assert store._st is None

