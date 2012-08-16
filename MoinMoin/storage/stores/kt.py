# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - kyoto tycoon store

Stores k/v pairs into a Kyoto Tycoon server. Kyoto Tycoon is a network server
for kyoto cabinet, remote or multi-process usage is possible).
"""


from __future__ import absolute_import, division

import time
import urllib
from httplib import HTTPConnection

from StringIO import StringIO

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase


class _Store(MutableStoreBase):
    """
    Kyoto tycoon based store.
    """
    @classmethod
    def from_uri(cls, uri):
        params = uri.split(':')
        if len(params) == 2:
            params[1] = int(params[1])
        return cls(*params)

    def __init__(self, host='127.0.0.1', port=1978, timeout=30):
        """
        Store params for .open().

        :param host: Tycoon server, host (default: '127.0.0.1')
        :param port: Tycoon server, port (default: 1978)
        :param timeout: timeout [s] (default: 30)
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    def create(self):
        self.open()
        self._clear()
        self.close()

    def destroy(self):
        self.open()
        self._clear()
        self.close()

    def open(self):
        self.client = HTTPConnection(self.host, self.port, False, self.timeout)

    def close(self):
        self.client.close()

    def _rpc(self, method, **kw):
        # note: we use rpc for some stuff that is not possible with restful interface
        # like iteration over keys, or for stuff that is simpler with rpc.
        kw = dict([(k, v) for k, v in kw.items() if v is not None])
        path_qs = '/rpc/{0}?{1}'.format(method, urllib.urlencode(kw))
        # we use GET with url args, it is simpler and enough for our purposes:
        self.client.request("GET", path_qs)
        response = self.client.getresponse()
        body = response.read()
        body = body.decode('utf-8')
        result = dict([line.rstrip('\r\n').split('\t') for line in body.splitlines()])
        status = response.status
        return status, result

    def _clear(self, DB=None):
        status, result = self._rpc('clear', DB=DB)
        assert status == 200

    def __iter__(self):
        cursor_id = '0'
        status, _ = self._rpc('cur_jump', DB=None, CUR=cursor_id, key=None)
        # we may get status != 200 early, if there is nothing at all in the store
        while status == 200:
            status, result = self._rpc('cur_get_key', CUR=cursor_id, step=True)
            if status == 200:
                yield result['key']

    def __delitem__(self, key):
        status, _ = self._rpc('remove', DB=None, key=key)
        assert status == 200


class BytesStore(_Store, BytesMutableStoreBase):
    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.set(key, value)

    def get(self, key):
        if isinstance(key, unicode):
            key = key.encode("utf-8")
        key = "/" + urllib.quote(key)
        self.client.request("GET", key)
        response = self.client.getresponse()
        body = response.read()
        if response.status != 200:
            return None
        return body

    def set(self, key, value, xt=None):
        if isinstance(key, unicode):
            key = key.encode("utf-8")
        key = "/" + urllib.quote(key)
        headers = {}
        if xt is not None:
            xt = int(time.time()) + xt
            headers["X-Kt-Xt"] = str(xt)
        self.client.request("PUT", key, value, headers)
        response = self.client.getresponse()
        body = response.read()
        return response.status == 201


class FileStore(_Store, FileMutableStoreBase):
    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, stream):
        self.set(key, stream)

    def get(self, key):
        if isinstance(key, unicode):
            key = key.encode("utf-8")
        key = "/" + urllib.quote(key)
        self.client.request("GET", key)
        response = self.client.getresponse()
        if response.status != 200:
            return None
        return response # XXX can we do that?

    def set(self, key, value, xt=None):
        if isinstance(key, unicode):
            key = key.encode("utf-8")
        key = "/" + urllib.quote(key)
        headers = {}
        if xt is not None:
            xt = int(time.time()) + xt
            headers["X-Kt-Xt"] = str(xt)
        value = value.read() # XXX reads value file into memory
        self.client.request("PUT", key, value, headers)
        response = self.client.getresponse()
        body = response.read()
        return response.status == 201
