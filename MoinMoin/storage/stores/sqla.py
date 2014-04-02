# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlalchemy store

Stores k/v pairs into any database supported by sqlalchemy.
"""


from __future__ import absolute_import, division

from sqlalchemy import create_engine, select, MetaData, Table, Column, String, Binary
from sqlalchemy.pool import StaticPool

from . import (BytesMutableStoreBase, FileMutableStoreBase,
               BytesMutableStoreMixin, FileMutableStoreMixin)

KEY_LEN = 128
VALUE_LEN = 1024 * 1024  # 1MB binary data


class BytesStore(BytesMutableStoreBase):
    """
    A simple dict-based in-memory store. No persistence!
    """
    @classmethod
    def from_uri(cls, uri):
        """
        Create a new cls instance from the using the uri

        :param cls: Class to create
        :param uri: The database uri that we pass on to SQLAlchemy.
        """
        # using "::" to support windows pathnames that
        # may include ":" after the drive letter.
        params = uri.split("::")
        return cls(*params)

    def __init__(self, db_uri=None, table_name='store', verbose=False):
        """
        :param db_uri: The database uri that we pass on to SQLAlchemy.
                       May contain user/password/host/port/etc.
        :param verbose: Verbosity setting. If set to True this will print all SQL queries
                        to the console.
        """
        self.db_uri = db_uri
        self.verbose = verbose
        self.engine = None
        self.table = None
        self.table_name = table_name

    def open(self):
        db_uri = self.db_uri
        if db_uri is None:
            # These are settings that apply only for development / testing only. The additional args are necessary
            # due to some limitations of the in-memory sqlite database.
            db_uri = 'sqlite:///:memory:'
            self.engine = create_engine(db_uri, poolclass=StaticPool, connect_args={'check_same_thread': False})
        else:
            self.engine = create_engine(db_uri, echo=self.verbose, echo_pool=self.verbose)

        metadata = MetaData()
        metadata.bind = self.engine
        self.table = Table(self.table_name, metadata,
                           Column('key', String(KEY_LEN), primary_key=True),
                           Column('value', Binary(VALUE_LEN)),
                          )

    def close(self):
        self.engine.dispose()
        self.table = None

    def create(self):
        self.open()
        self.table.create()
        self.close()

    def destroy(self):
        self.open()
        self.table.drop()
        self.close()

    def __iter__(self):
        rows = select([self.table.c.key]).execute().fetchall()
        for row in rows:
            yield row[0]

    def __delitem__(self, key):
        self.table.delete().where(self.table.c.key == key).execute()

    def __getitem__(self, key):
        value = select([self.table.c.value], self.table.c.key == key).execute().fetchone()
        if value is not None:
            return value[0]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.table.insert().execute(key=key, value=value)


class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase):
    """sqlalchemy FileStore"""
