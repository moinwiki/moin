# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - serializer / deserializer tests
"""


from __future__ import absolute_import, division

from io import BytesIO

import pytest

from ..indexing import IndexingMiddleware, WHOOSH_FILESTORAGE
from ..routing import Backend as RoutingBackend
from ..serialization import serialize, deserialize

from moin.constants.keys import NAME, CONTENTTYPE
from moin.constants.namespaces import NAMESPACE_DEFAULT

from moin.storage.backends.stores import MutableBackend
from moin.storage.stores.memory import BytesStore, FileStore


contents = [
    (u'Foo', {NAME: [u'Foo', ], CONTENTTYPE: u'text/plain;charset=utf-8'}, ''),
    (u'Foo', {NAME: [u'Foo', ], CONTENTTYPE: u'text/plain;charset=utf-8'}, '2nd'),
    (u'Subdir', {NAME: [u'Subdir', ], CONTENTTYPE: u'text/plain;charset=utf-8'}, ''),
    (u'Subdir/Foo', {NAME: [u'Subdir/Foo', ], CONTENTTYPE: u'text/plain;charset=utf-8'}, ''),
    (u'Subdir/Bar', {NAME: [u'Subdir/Bar', ], CONTENTTYPE: u'text/plain;charset=utf-8'}, ''),
]


scenarios = [
    ('Simple', ['']),
    ('Nested', ['', 'Subdir']),
]


def pytest_generate_tests(metafunc):
    metafunc.parametrize('source,target', [('Simple', 'Simple'), ], ids=['Simple->Simple', ], indirect=True)


@pytest.fixture
def source(request):
    # scenario
    return make_middleware(request)


@pytest.fixture
def target(request):
    # scenario
    return make_middleware(request)


def make_middleware(request):
    tmpdir = request.getfuncargvalue('tmpdir')
    # scenario

    meta_store = BytesStore()
    data_store = FileStore()
    _backend = MutableBackend(meta_store, data_store)
    namespaces = [(NAMESPACE_DEFAULT, u'backend')]
    backends = {u'backend': _backend}
    backend = RoutingBackend(namespaces, backends)
    backend.create()
    backend.open()
    request.addfinalizer(backend.destroy)
    request.addfinalizer(backend.close)

    mw = IndexingMiddleware(index_storage=(WHOOSH_FILESTORAGE, (str(tmpdir / 'foo'), ), {}),
                            backend=backend)
    mw.create()
    mw.open()
    request.addfinalizer(mw.destroy)
    request.addfinalizer(mw.close)
    return mw


def test_serialize_deserialize(source, target):
    i = 0
    for name, meta, data in contents:
        item = source[name]
        item.store_revision(dict(meta, mtime=i), BytesIO(data))
        i += 1

    io = BytesIO()
    serialize(source.backend, io)
    io.seek(0)
    deserialize(io, target.backend)
    target.rebuild()

    print sorted(source.backend)
    print sorted(target.backend)
    assert sorted(source.backend) == sorted(target.backend)
