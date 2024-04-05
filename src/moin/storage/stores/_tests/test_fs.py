# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - fs store tests
"""

import pytest

from ..fs import BytesStore, FileStore


@pytest.mark.parametrize("Store", [BytesStore, FileStore])
def test_create_and_destroy(tmpdir, Store):
    target = tmpdir.join("store")
    assert not target.check()
    store = Store(str(target))
    assert not target.check()
    store.create()
    assert target.check()
    store.destroy()
    assert not target.check()


@pytest.mark.parametrize("Store", [BytesStore, FileStore])
def test_from_uri(tmpdir, Store):
    store = Store.from_uri("%s" % tmpdir)
    assert store.path == tmpdir
