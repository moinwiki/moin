# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - routing middleware tests
"""


from __future__ import absolute_import, division

from StringIO import StringIO

import pytest

from MoinMoin.constants.keys import NAME, NAMESPACE

from ..routing import Backend as RoutingBackend

from MoinMoin.storage.backends.stores import MutableBackend as StoreBackend, Backend as ROBackend
from MoinMoin.storage.stores.memory import BytesStore as MemoryBytesStore
from MoinMoin.storage.stores.memory import FileStore as MemoryFileStore


def make_ro_backend():
    store = StoreBackend(MemoryBytesStore(), MemoryFileStore())
    store.create()
    store.open()
    store.store({NAME: 'test'}, StringIO(''))
    store.store({NAME: 'test2'}, StringIO(''))
    return ROBackend(store.meta_store, store.data_store)


def pytest_funcarg__router(request):
    default_be = StoreBackend(MemoryBytesStore(), MemoryFileStore())
    other_be = StoreBackend(MemoryBytesStore(), MemoryFileStore())
    ro_be = make_ro_backend()
    namespaces = [(u'other:', 'other'), (u'ro:', 'ro'), (u'', 'default')]
    backends = {'other': other_be, 'ro': ro_be, 'default': default_be, }
    router = RoutingBackend(namespaces, backends)
    router.create()
    router.open()

    @request.addfinalizer
    def finalize():
        router.close()
        router.destroy()

    return router


def test_store_get_del(router):
    default_name = u'foo'
    default_backend_name, default_revid = router.store(dict(name=[default_name, ]), StringIO(''))
    other_name = u'other:bar'
    other_backend_name, other_revid = router.store(dict(name=[other_name, ]), StringIO(''))

    # check if store() updates the to-store metadata with correct NAMESPACE and NAME
    default_meta, _ = router.retrieve(default_backend_name, default_revid)
    other_meta, _ = router.retrieve(other_backend_name, other_revid)
    assert u'' == default_meta[NAMESPACE]
    assert [default_name, ] == default_meta[NAME]
    assert other_name.split(':')[0] == other_meta[NAMESPACE]
    assert other_name.split(':')[1] == other_meta[NAME][0]

    # delete revs:
    router.remove(default_backend_name, default_revid)
    router.remove(other_backend_name, other_revid)


def test_store_readonly_fails(router):
    with pytest.raises(TypeError):
        router.store(dict(name=[u'ro:testing', ]), StringIO(''))


def test_del_readonly_fails(router):
    ro_be_name, ro_id = next(iter(router))  # we have only readonly items
    print ro_be_name, ro_id
    with pytest.raises(TypeError):
        router.remove(ro_be_name, ro_id)


def test_destroy_create_dont_touch_ro(router):
    existing = set(router)
    default_be_name, default_revid = router.store(dict(name=[u'foo', ]), StringIO(''))
    other_be_name, other_revid = router.store(dict(name=[u'other:bar', ]), StringIO(''))

    router.close()
    router.destroy()
    router.create()
    router.open()

    assert set(router) == existing


def test_iter(router):
    existing_before = set([revid for be_name, revid in router])
    default_be_name, default_revid = router.store(dict(name=[u'foo', ]), StringIO(''))
    other_be_name, other_revid = router.store(dict(name=[u'other:bar', ]), StringIO(''))
    existing_now = set([revid for be_name, revid in router])
    assert existing_now == set([default_revid, other_revid]) | existing_before
