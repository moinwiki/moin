# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - kyoto cabinet store tests
"""


from __future__ import absolute_import, division

import pytest
pytest.importorskip('storage.stores.kc')

from ..kc import BytesStore, FileStore


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(tmpdir, Store):
    target = tmpdir.join('store.kch')
    assert not target.check()

    store = Store(str(target))
    assert not target.check()
    store.create()
    assert target.check()

    return store


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(tmpdir, Store):
    store = test_create(tmpdir, Store)
    target = tmpdir.join('store.kch')
    store.destroy()
    assert not target.check()


