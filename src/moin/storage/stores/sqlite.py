# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - SQLite key/value store.

This store stores data in a SQLite table, using a single DB file in the file system.
You can use the same DB file for multiple stores by using different table names.

Optionally, zlib ("gzip") compression can be used.
"""

import os
import base64
import zlib
from sqlite3 import connect, Row, IntegrityError

from moin.constants.namespaces import NAMESPACE_USERPROFILES
from . import BytesMutableStoreBase, FileMutableStoreBase, FileMutableStoreMixin


class BytesStore(BytesMutableStoreBase):
    """
    A simple SQLite-based store.
    """

    @classmethod
    def from_uri(cls, uri):
        """
        Create a new cls instance from the given URI.

        :param cls: Class to create
        :param uri: The URI should follow the template
                    db_name::table_name::compression_level
                    where table_name and compression_level are optional
        """
        # Using "::" to support Windows pathnames that
        # may include ":" after the drive letter.
        params = uri.split("::")
        if len(params) == 3:
            params[2] = int(params[2])
        return cls(*params)

    def __init__(self, db_name, table_name="store", compression_level=0):
        """
        Just store the params.

        :param db_name: Database (file) name
        :param table_name: Table to use for this store (we only touch this table)
        :param compression_level: zlib compression level
                                  0 = no compression, 1 = fast/small, ..., 9 = slow/smaller
                                  We recommend 0 for low CPU usage, 1 for low disk space usage.
                                  Higher compression levels do not give much better compression
                                  but use lots of CPU (e.g., 6 is about 2× more CPU than 1).
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
        # We store magic start/end markers and the compression level,
        # so we can later decompress correctly (or rather not decompress if level == 0)
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
        value = str(rows[0]["value"])  # a string in base64 encoding
        value = base64.b64decode(value.encode())
        return self._decompress(value)

    def __setitem__(self, key, value):
        value = self._compress(value)
        with self.conn:
            value = base64.b64encode(value).decode()  # a string in base64 encoding
            try:
                self.conn.execute(f"insert into {self.table_name} values (?, ?)", (key, value))
            except IntegrityError:
                if NAMESPACE_USERPROFILES in self.db_name:
                    # The userprofiles namespace does not support revisions, so we update the existing row
                    self.conn.execute(
                        'UPDATE {0} SET value = "{2}" WHERE key = "{1}"'.format(self.table_name, key, value)
                    )
                else:
                    raise


class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase):
    """SQLite FileStore."""
