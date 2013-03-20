# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - store tests
"""


from __future__ import absolute_import, division

import pytest


def test_getitem_raises(store):
    with pytest.raises(KeyError):
        store['doesnotexist']


def test_setitem_getitem_delitem(store):
    k, v = 'key', 'value'
    store[k] = v
    assert v == store[k]
    del store[k]
    with pytest.raises(KeyError):
        store[k]


def test_setitem_getitem_delitem_binary(store):
    k, v = 'key', '\000\001\002'
    store[k] = v
    assert v == store[k]
    assert len(v) == 3
    del store[k]
    with pytest.raises(KeyError):
        store[k]


def test_iter(store):
    kvs = set([('1', 'one'), ('2', 'two'), ('3', 'three'), ])
    for k, v in kvs:
        store[k] = v
    result = set()
    for k in store:
        result.add((k, store[k]))
    assert result == kvs


def test_len(store):
    assert len(store) == 0
    store['foo'] = 'bar'
    assert len(store) == 1
    del store['foo']
    assert len(store) == 0


def test_perf(store):
    # XXX: introduce perf test option
    pytest.skip("usually we do no performance tests")
    for i in range(1000):
        key = value = str(i)
        store[key] = value
    for i in range(1000):
        key = expected_value = str(i)
        assert store[key] == expected_value
    for i in range(1000):
        key = str(i)
        del store[key]
