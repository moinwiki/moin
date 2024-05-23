# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - sqlalchemy store

Stores k/v pairs into any database supported by sqlalchemy.
"""

import os

from sqlalchemy import create_engine, select, MetaData, Table, Column, String, LargeBinary
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from moin.constants.namespaces import NAMESPACE_USERPROFILES
from . import BytesMutableStoreBase, FileMutableStoreBase, FileMutableStoreMixin

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

    def __init__(self, db_uri=None, table_name="store", verbose=False):
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
        if db_uri.startswith("sqlite:///"):
            db_path = os.path.dirname(self.db_uri.split("sqlite:///")[1])
            if db_path and not os.path.exists(db_path):
                os.makedirs(db_path)

    def open(self):
        db_uri = self.db_uri
        if db_uri is None:
            # These are settings that apply only for development / testing only. The additional args are necessary
            # due to some limitations of the in-memory sqlite database.
            db_uri = "sqlite:///:memory:"
            self.engine = create_engine(db_uri, poolclass=StaticPool, connect_args={"check_same_thread": False})
        else:
            self.engine = create_engine(db_uri, echo=self.verbose, echo_pool=self.verbose)

        self.metadata = MetaData()
        self.table = Table(
            self.table_name,
            self.metadata,
            Column("key", String(KEY_LEN), primary_key=True),
            Column("value", LargeBinary(VALUE_LEN)),
        )

    def close(self):
        self.engine.dispose()
        self.table = None

    def create(self):
        self.open()
        with self.engine.connect() as conn:
            with conn.begin():
                self.metadata.create_all(conn)
        self.close()

    def destroy(self):
        self.open()
        with self.engine.connect() as conn:
            with conn.begin():
                self.metadata.drop_all(conn)
        self.close()

    def __iter__(self):
        with self.engine.connect() as conn:
            rows = conn.execute(select(self.table.c.key))
            for row in rows:
                yield row[0]

    def __delitem__(self, key):
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(self.table.delete().where(self.table.c.key == key))

    def __getitem__(self, key):
        with self.engine.connect() as conn:
            value = conn.execute(select(self.table.c.value).where(self.table.c.key == key)).fetchone()
            if value is not None:
                return value[0]
            else:
                raise KeyError(key)

    def __setitem__(self, key, value):
        with self.engine.connect() as conn:
            with conn.begin():
                try:
                    conn.execute(self.table.insert().values(key=key, value=value))
                except IntegrityError:
                    if NAMESPACE_USERPROFILES in self.db_uri:
                        # userprofiles namespace does support revisions so we update existing row
                        conn.execute(self.table.update().values(key=key, value=value))
                    else:
                        raise


class FileStore(FileMutableStoreMixin, BytesStore, FileMutableStoreBase):
    """sqlalchemy FileStore"""
