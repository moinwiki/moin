# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - store test magic
"""

import pytest
from ..wrappers import ByteToStreamWrappingStore

STORES_PACKAGE = "moin.storage.stores"

STORES = "fs memory sqlite sqlite:compressed sqla".split()


constructors = {
    "memory": lambda store, _: store(),
    "fs": lambda store, tmpdir: store(str(tmpdir.join("store"))),
    "sqlite": lambda store, tmpdir: store(str(tmpdir.join("store.sqlite")), "test_table", compression_level=0),
    "sqlite:compressed": lambda store, tmpdir: store(
        str(tmpdir.join("store.sqlite")), "test_table", compression_level=1
    ),
    "sqla": lambda store, tmpdir: store("sqlite:///{!s}".format(tmpdir.join("store.sqlite")), "test_table"),
}


def pytest_generate_tests(metafunc):
    argnames = metafunc.fixturenames

    if "store" in argnames:
        klasses = "BytesStore", "FileStore"
        argname = "store"
    elif "bst" in argnames:
        klasses = ("BytesStore",)
        argname = "bst"
    elif "fst" in argnames:
        klasses = ("FileStore",)
        argname = "fst"
    else:
        klasses = None
        argname = None

    if klasses is not None:
        ids = []
        argvalues = []
        for storename in STORES:
            for klass in klasses:
                ids.append(f"{storename}/{klass}")
                argvalues.append((storename, klass))
        metafunc.parametrize(argname, argvalues, ids=ids, indirect=True)

    multi_mark = metafunc.definition.get_closest_marker("multi")
    if multi_mark is not None:
        ids = []
        argvalues = []
        stores = multi_mark.kwargs["Store"]
        for store in stores:
            ids.append(store.__name__)
            argvalues.append(store)
        metafunc.parametrize("Store", argvalues, ids=ids)


def make_store(request, tmpdir):
    storename, kind = request.param
    storemodule = pytest.importorskip(STORES_PACKAGE + "." + storename.split(":")[0])
    klass = getattr(storemodule, kind)
    construct = constructors.get(storename)
    if construct is None:
        pytest.xfail(f"don't know how to construct {storename} store")
    store = construct(klass, tmpdir)
    store.create()
    store.open()
    request.addfinalizer(store.close)
    # for debugging, you can disable the next line to see the stuff in the
    # store and examine it, but usually we want to clean up afterwards:
    request.addfinalizer(store.destroy)
    return store


@pytest.fixture
def bst(request):
    return make_store(request)


@pytest.fixture
def fst(request):
    return make_store(request)


@pytest.fixture
def store(request, tmpdir):
    store = make_store(request, tmpdir)
    storename, kind = request.param
    if kind == "FileStore":
        store = ByteToStreamWrappingStore(store)
    # store here always is a ByteStore and can be tested as such
    return store
