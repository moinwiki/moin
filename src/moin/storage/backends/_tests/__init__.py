# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend tests
"""

from io import BytesIO

import pytest

from moin.constants.keys import SIZE, HASH_ALGORITHM


class BackendTestBase:
    def setup_method(self, method):
        """
        self.be needs to be an opened backend
        """
        raise NotImplementedError

    def teardown_method(self, method):
        """
        close self.be
        """
        self.be.close()

    def test_getrevision_raises(self):
        with pytest.raises(KeyError):
            self.be.retrieve("doesnotexist")

    def test_iter(self):
        assert list(self.be) == []


class MutableBackendTestBase(BackendTestBase):
    def setup_method(self, method):
        """
        self.be needs to be an created/opened backend
        """
        raise NotImplementedError

    def teardown_method(self, method):
        """
        close and destroy self.be
        """
        self.be.close()
        self.be.destroy()

    def test_getrevision_raises(self):
        with pytest.raises(KeyError):
            self.be.retrieve("doesnotexist")

    def test_store_get_del(self):
        meta = dict(foo="bar")
        data = b"baz"
        metaid = self.be.store(meta, BytesIO(data))
        m, d = self.be.retrieve(metaid)
        assert m == meta
        assert d.read() == data
        d.close()
        self.be.remove(metaid, destroy_data=True)
        with pytest.raises(KeyError):
            self.be.retrieve(metaid)

    def test_store_check_size(self):
        # no size
        meta = dict(name="foo")
        data = b"barbaz"
        metaid = self.be.store(meta, BytesIO(data))
        m, d = self.be.retrieve(metaid)
        assert meta[SIZE] == 6
        # correct size
        meta = dict(name="foo", size=6)
        data = b"barbaz"
        metaid = self.be.store(meta, BytesIO(data))
        m, d = self.be.retrieve(metaid)
        assert meta[SIZE] == 6
        # wrong size (less data than size declared in meta)
        meta = dict(name="foo", size=42)
        data = b"barbaz"
        with pytest.raises(ValueError):
            metaid = self.be.store(meta, BytesIO(data))
        # wrong size (more data than size declared in meta)
        meta = dict(name="foo", size=3)
        data = b"barbaz"
        with pytest.raises(ValueError):
            metaid = self.be.store(meta, BytesIO(data))

    def test_store_check_hash(self):
        # no hash
        meta = dict(name="foo")
        data = b"barbaz"
        metaid = self.be.store(meta, BytesIO(data))
        m, d = self.be.retrieve(metaid)
        hashcode = meta[HASH_ALGORITHM]
        # correct hash
        meta = dict(name="foo")
        meta[HASH_ALGORITHM] = hashcode
        data = b"barbaz"
        metaid = self.be.store(meta, BytesIO(data))
        m, d = self.be.retrieve(metaid)
        assert meta[HASH_ALGORITHM] == hashcode
        # wrong data -> hash mismatch
        meta = dict(name="foo")
        meta[HASH_ALGORITHM] = hashcode
        data = b"brrbrr"
        with pytest.raises(ValueError):
            metaid = self.be.store(meta, BytesIO(data))

    def test_iter(self):
        mds = [  # (metadata items, data str)
            (dict(name="one"), b"ONE"),
            (dict(name="two"), b"TWO"),
            (dict(name="three"), b"THREE"),
        ]
        expected_result = set()
        for m, d in mds:
            k = self.be.store(m, BytesIO(d))
            # note: store_revision injects some new keys (like dataid, metaid, size, hash key) into m
            m = tuple(sorted(m.items()))
            expected_result.add((k, m, d))
        result = set()
        for k in self.be:
            m, d = self.be.retrieve(k)
            m = tuple(sorted(m.items()))
            result.add((k, m, d.read()))
        assert result == expected_result
