# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - router middleware tests
"""


from __future__ import absolute_import, division

from StringIO import StringIO

import pytest

from MoinMoin.config import NAME, REVID

from ..routing import Backend as RouterBackend

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
    root_be = StoreBackend(MemoryBytesStore(), MemoryFileStore())
    sub_be = StoreBackend(MemoryBytesStore(), MemoryFileStore())
    ro_be = make_ro_backend()
    router = RouterBackend([('sub', sub_be), ('ro', ro_be), ('', root_be)])
    router.create()
    router.open()

    @request.addfinalizer
    def finalize():
        router.close()
        router.destroy()

    return router

def revid_split(revid):
    # router revids are <backend_mountpoint>:<backend_revid>, split that:
    return revid.rsplit(u':', 1)

def test_store_get_del(router):
    root_name = u'foo'
    root_revid = router.store(dict(name=root_name), StringIO(''))
    sub_name = u'sub/bar'
    sub_revid = router.store(dict(name=sub_name), StringIO(''))

    assert revid_split(root_revid)[0] == ''
    assert revid_split(sub_revid)[0] == 'sub'

    # when going via the router backend, we get back fully qualified names:
    root_meta, _ = router.retrieve(root_revid)
    sub_meta, _ = router.retrieve(sub_revid)
    assert root_name == root_meta[NAME]
    assert sub_name == sub_meta[NAME]

    # when looking into the storage backend, we see relative names (without mountpoint):
    root_meta, _ = router.mapping[-1][1].retrieve(revid_split(root_revid)[1])
    sub_meta, _ = router.mapping[0][1].retrieve(revid_split(sub_revid)[1])
    assert root_name == root_meta[NAME]
    assert sub_name == 'sub' + '/' + sub_meta[NAME]
    # delete revs:
    router.remove(root_revid)
    router.remove(sub_revid)


def test_store_readonly_fails(router):
    with pytest.raises(TypeError):
        router.store(dict(name=u'ro/testing'), StringIO(''))

def test_del_readonly_fails(router):
    ro_id = next(iter(router)) # we have only readonly items
    print ro_id
    with pytest.raises(TypeError):
        router.remove(ro_id)


def test_destroy_create_dont_touch_ro(router):
    existing = set(router)
    root_revid = router.store(dict(name=u'foo'), StringIO(''))
    sub_revid = router.store(dict(name=u'sub/bar'), StringIO(''))

    router.close()
    router.destroy()
    router.create()
    router.open()

    assert set(router) == existing


def test_iter(router):
    existing = set(router)
    root_revid = router.store(dict(name=u'foo'), StringIO(''))
    sub_revid = router.store(dict(name=u'sub/bar'), StringIO(''))
    assert set(router) == (set([root_revid, sub_revid])|existing)

