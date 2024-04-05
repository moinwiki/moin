# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlite3 key/value store

This store stores into sqlite3 table, using a single db file in the filesystem.
You can use the same db file for multiple stores, just using a different table
name.

Optionally, you can use zlib/"gzip" compression.
"""

import os
import base64
import zlib
from sqlite3 import connect, Row, IntegrityError

from moin.constants.namespaces import NAMESPACE_USERPROFILES
from . import BytesMutableStoreBase, FileMutableStoreBase, FileMutableStoreMixin


class BytesStore(BytesMutableStoreBase):
    """
    A simple sqlite3 based store.
    """

    @classmethod
    def from_uri(cls, uri):
        """
        Create a new cls instance using the parameters provided in the uri

        :param cls: Class to create
        :param uri: The URI should follow the following template
                    db_name::table_name::compression_level
                    where table_name and compression level are optional
        """
        # using "::" to support windows pathnames that
        # may include ":" after the drive letter.
        params = uri.split("::")
        if len(params) == 3:
            params[2] = int(params[2])
        return cls(*params)

    def __init__(self, db_name, table_name="store", compression_level=0):
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
        db_path = os.path.dirname(self.db_name)
        if not os.path.exists(db_path):
            os.makedirs(db_path)

    def create(self):
        conn = connect(self.db_name)
        with conn:
            conn.execute(f"create table {self.table_name} (key text primary key, value blob)")

    def destroy(self):
        conn = connect(self.db_name)
        with conn:
            conn.execute(f"drop table {self.table_name}")

    def open(self):
        self.conn = connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = Row  # make column access by ['colname'] possible

    def close(self):
        pass

    def __iter__(self):
        for row in self.conn.execute(f"select key from {self.table_name}"):
            yield row["key"]

    def __delitem__(self, key):
        with self.conn:
            self.conn.execute(f"delete from {self.table_name} where key=?", (key,))

    def _compress(self, value):
        if self.compression_level:
            value = zlib.compress(value, self.compression_level)
        # we store some magic start/end markers and the compression level,
        # so we can later uncompress correctly (or rather NOT uncompress if level == 0)
        header = "{{{GZ%d|" % self.compression_level
        tail = "}}}"
        return header.encode() + value + tail.encode()

    def _decompress(self, value):
        if not (value[:5] == b"{{{GZ" and value[-3:] == b"}}}"):
            print("value = %r ... %r" % (value[:5], value[-3:]))
            raise ValueError("Invalid data format in database.")
        compression_level = int(chr(value[5]))
        value = value[7:-3]
        if compression_level:
            value = zlib.decompress(value)
        return value

    def __getitem__(self, key):
        rows = list(self.conn.execute(f"select value from {self.table_name} where key=?", (key,)))
        if not rows:
            raise KeyError(key)
        value = str(rows[0]["value"])  # a str in base64 encoding
        value = base64.b64decode(value.encode())
        return self._decompress(value)

    def __setitem__(self, key, value):
        value = self._compress(value)
        with self.conn:
            value = base64.b64encode(value).decode()  # a str in base64 encoding
            try:
                self.conn.execute(f"insert into {self.table_name} values (?, ?)", (key, value))
            except IntegrityError:
                if NAMESPACE_USERPROFILES in self.db_name:
                    # userprofiles namespace does support revisions so we update existing row
                    self.conn.execute(
                        'UPDATE {0} SET value = "{2}" WHERE key = "{1}"'.format(self.table_name, key, value)
                    )
                else:
                    raise


class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase):
    """sqlite FileStore"""
