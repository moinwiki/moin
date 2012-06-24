# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - fs store tests
"""


from __future__ import absolute_import, division

import pytest

from ..fs import BytesStore, FileStore


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_create(tmpdir, Store):
    target = tmpdir.join('store')
    assert not target.check()

    store = Store(str(target))
    assert not target.check()
    store.create()
    assert target.check()

    return store


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_destroy(tmpdir, Store):
    store = test_create(tmpdir, Store)
    target = tmpdir.join('store')
    store.destroy()
    assert not target.check()


@pytest.mark.multi(Store=[BytesStore, FileStore])
def test_from_uri(tmpdir, Store):
    store = Store.from_uri("%s" % tmpdir)
    assert store.path == tmpdir
