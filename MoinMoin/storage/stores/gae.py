# Copyright: 2011 MoinMoin:GuidoVanRossum
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Google App Engine store

Store into Google App Engine datastore (using NDB), one entity per k/v pair.
"""

from __future__ import absolute_import, division

import cStringIO as StringIO
import logging

from google.appengine.ext import ndb

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase


class _MoinDirectory(ndb.Model):
    """Used as a parent key."""


class _MoinValue(ndb.Model):
    """Used to store a value.

    The parent is a _MoinDirectory key (but no _MoinDirectory
    object exists).
    """

    value = ndb.BlobProperty()


class _Store(MutableStoreBase):
    """Keys and uris are required to be valid key names.

    (This is not an onerous requirement.)
    """

    @classmethod
    def from_uri(cls, uri):
        return cls(uri)

    def __init__(self, path):
        logging.info('%s(%r)', self.__class__.__name__, path)
        self._root_key = ndb.Key(_MoinDirectory, path)
        self._query = _MoinValue.query(ancestor=self._root_key)

    def create(self):
        """Nothing to do."""

    def destroy(self):
        self._query.map(self._destroy_key, keys_only=True)

    def _destroy_key(self, key):
        return key.delete()

    def __iter__(self):
        return self._query.iter(keys_only=True)

    def _getitem(self, key):
        ent = _MoinValue.get_by_id(key, parent=self._root_key)
        return ent and ent.value or 'null'

    def _setitem(self, key, value):
        _MoinValue(value=value, id=key, parent=self._root_key).put()

    def __delitem__(self, key):
        ndb.Key(_MoinValue, key, parent=self._root_key).delete()


class BytesStore(_Store, BytesMutableStoreBase):

    def __getitem__(self, key):
        return self._getitem(key)
    
    def __setitem__(self, key, value):
        self._setitem(key, value)


class FileStore(_Store, FileMutableStoreBase):

    def __getitem__(self, key):
        return StringIO.StringIO(self._getitem(key))

    def __setitem__(self, key, stream):
        return self._setitem(key, stream.read())
