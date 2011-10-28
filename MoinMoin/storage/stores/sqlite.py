# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlite3 key/value store

This store stores into sqlite3 table, using a single db file in the filesystem.
You can use the same db file for multiple stores, just using a different table
name.

Optionally, you can use zlib/"gzip" compression.
"""


from __future__ import absolute_import, division

from StringIO import StringIO
import zlib
from sqlite3 import *

from . import MutableStoreBase, BytesMutableStoreBase, FileMutableStoreBase


class _Store(MutableStoreBase):
    """
    A simple sqlite3 based store.
    """
    @classmethod
    def from_uri(cls, uri):
        """
        Create a new cls instance from the using the uri

        :param cls: Class to create
        :param uri: The URI should follow the following template
                    db_name:table_name:compression_level
                    where table_name and compression level are optional
        """
        params = uri.split(":")
        if len(params) == 3:
            params[2] = int(params[2])
        return cls(*params)

    def __init__(self, db_name, table_name='store', compression_level=0):
        """
        Just store the params.

        :param db_name: database (file)name
        :param table_name: table to use for this store (we only touch this table)
        :param compression_level: zlib compression level
                                  0 = no compr, 1 = fast/small, ..., 9 = slow/smaller
                                  we recommend 0 for low cpu usage, 1 for low disk space usage
                                  high compression levels don't give much better compression,
                                  but use lots of cpu (e.g. 6 is about 2x more cpu than 1).
        """
        self.db_name = db_name
        self.table_name = table_name
        self.compression_level = compression_level

    def create(self):
        conn = connect(self.db_name)
        with conn:
            conn.execute('create table {0} (key text primary key, value blob)'.format(self.table_name))

    def destroy(self):
        conn = connect(self.db_name)
        with conn:
            conn.execute('drop table {0}'.format(self.table_name))

    def open(self):
        self.conn = connect(self.db_name)
        self.conn.row_factory = Row # make column access by ['colname'] possible

    def close(self):
        pass

    def __iter__(self):
        for row in self.conn.execute("select key from {0}".format(self.table_name)):
            yield row['key']

    def __delitem__(self, key):
        with self.conn:
            self.conn.execute('delete from {0} where key=?'.format(self.table_name), (key, ))

    def _compress(self, value):
        if self.compression_level:
            value = zlib.compress(value, self.compression_level)
        # we store some magic start/end markers and the compression level,
        # so we can later uncompress correctly (or rather NOT uncompress if level == 0)
        return "{{{GZ%(level)d|%(value)s}}}" % dict(level=self.compression_level, value=value)

    def _decompress(self, value):
        if not value.startswith("{{{GZ") or not value.endswith("}}}"):
            raise ValueError("Invalid data format in database.")
        compression_level = int(value[5])
        value = value[7:-3]
        if compression_level:
            value = zlib.decompress(value)
        return value


class BytesStore(_Store, BytesMutableStoreBase):
    def __getitem__(self, key):
        rows = list(self.conn.execute("select value from {0} where key=?".format(self.table_name), (key, )))
        if not rows:
            raise KeyError(key)
        value = str(rows[0]['value'])
        return self._decompress(value)

    def __setitem__(self, key, value):
        value = self._compress(value)
        with self.conn:
            self.conn.execute('insert into {0} values (?, ?)'.format(self.table_name), (key, buffer(value)))


class FileStore(_Store, FileMutableStoreBase):
    def __getitem__(self, key):
        rows = list(self.conn.execute("select value from {0} where key=?".format(self.table_name), (key, )))
        if not rows:
            raise KeyError(key)
        value = str(rows[0]['value'])
        return StringIO(self._decompress(value))

    def __setitem__(self, key, stream):
        value = stream.read()
        value = self._compress(value)
        with self.conn:
            self.conn.execute('insert into {0} values (?, ?)'.format(self.table_name), (key, buffer(value)))

