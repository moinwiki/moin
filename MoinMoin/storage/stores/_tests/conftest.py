# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - store test magic
"""


from __future__ import absolute_import, division

import pytest
from ..wrappers import ByteToStreamWrappingStore

from MoinMoin._tests import check_connection

STORES_PACKAGE = 'MoinMoin.storage.stores'

STORES = 'fs kc memory sqlite sqlite:compressed sqla'.split()
try:
    # check if we can connect to the kt server
    check_connection(1978)
    STORES.append('kt')
except Exception:
    pass

constructors = {
    'memory': lambda store, _: store(),
    'fs': lambda store, tmpdir: store(str(tmpdir.join('store'))),
    'sqlite': lambda store, tmpdir: store(str(tmpdir.join('store.sqlite')),
                                          'test_table', compression_level=0),
    'sqlite:compressed': lambda store, tmpdir: store(str(tmpdir.join('store.sqlite')),
                                          'test_table', compression_level=1),
    'kc': lambda store, tmpdir: store(str(tmpdir.join('store.kch'))),
    'kt': lambda store, _: store(),
    'sqla': lambda store, tmpdir: store('sqlite:///{0!s}'.format(tmpdir.join('store.sqlite')),
                                        'test_table'),
}


def pytest_generate_tests(metafunc):
    argnames = metafunc.funcargnames

    if 'store' in argnames:
        klasses = 'BytesStore', 'FileStore'
    elif 'bst' in argnames:
        klasses = 'BytesStore',
    elif 'fst' in argnames:
        klasses = 'FileStore',
    else:
        klasses = None

    if klasses is not None:
        for storename in STORES:
            for klass in klasses:
                metafunc.addcall(
                    id='{0}/{1}'.format(storename, klass),
                    param=(storename, klass))

    multi_mark = getattr(metafunc.function, 'multi', None)
    if multi_mark is not None:
        # XXX: hack
        stores = multi_mark.kwargs['Store']
        for store in stores:
            metafunc.addcall(id=store.__name__, funcargs={
                'Store': store,
            })


def make_store(request):
    tmpdir = request.getfuncargvalue('tmpdir')
    storename, kind = request.param
    storemodule = pytest.importorskip(STORES_PACKAGE + '.' + storename.split(':')[0])
    klass = getattr(storemodule, kind)
    construct = constructors.get(storename)
    if construct is None:
        pytest.xfail('don\'t know how to construct {0} store'.format(storename))
    store = construct(klass, tmpdir)
    store.create()
    store.open()
    # no destroy in the normal finalizer
    # so we can keep the data for example if it's a tmpdir
    request.addfinalizer(store.close)
    return store


def pytest_funcarg__bst(request):
    return make_store(request)


def pytest_funcarg__fst(request):
    return make_store(request)


def pytest_funcarg__store(request):
    store = make_store(request)
    storename, kind = request.param
    if kind == 'FileStore':
        store = ByteToStreamWrappingStore(store)
    return store

