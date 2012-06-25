# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - serializer / deserializer tests
"""


from __future__ import absolute_import, division

from StringIO import StringIO

from ..indexing import IndexingMiddleware
from ..routing import Backend as RoutingBackend
from ..serialization import serialize, deserialize

from MoinMoin.storage.backends.stores import MutableBackend
from MoinMoin.storage.stores.memory import BytesStore, FileStore


contents = [
    (u'Foo', {'name': u'Foo'}, ''),
    (u'Foo', {'name': u'Foo'}, '2nd'),
    (u'Subdir', {'name': u'Subdir'}, ''),
    (u'Subdir/Foo', {'name': u'Subdir/Foo'}, ''),
    (u'Subdir/Bar', {'name': u'Subdir/Bar'}, ''),
]


scenarios = [
    ('Simple', ['']),
    ('Nested', ['', 'Subdir']),
]


def pytest_generate_tests(metafunc):
    metafunc.addcall(id='Simple->Simple', param=('Simple', 'Simple'))

def pytest_funcarg__source(request):
    # scenario
    return make_middleware(request)

def pytest_funcarg__target(request):
    # scenario
    return make_middleware(request)

def make_middleware(request):
    tmpdir = request.getfuncargvalue('tmpdir')
    # scenario

    meta_store = BytesStore()
    data_store = FileStore()
    _backend = MutableBackend(meta_store, data_store)
    mapping = [('', _backend)]
    backend = RoutingBackend(mapping)
    backend.create()
    backend.open()
    request.addfinalizer(backend.destroy)
    request.addfinalizer(backend.close)

    mw = IndexingMiddleware(index_dir=str(tmpdir/'foo'),
                            backend=backend)
    mw.create()
    mw.open()
    request.addfinalizer(mw.destroy)
    request.addfinalizer(mw.close)
    return mw


def test_serialize_deserialize(source, target):
    i = 0
    for name, meta, data in contents:
        item = source['name']
        item.store_revision(dict(meta, mtime=i), StringIO(data))
        i += 1

    io = StringIO()
    serialize(source.backend, io)
    io.seek(0)
    deserialize(io, target.backend)
    target.rebuild()

    print sorted(source.backend)
    print sorted(target.backend)
    assert sorted(source.backend) == sorted(target.backend)
