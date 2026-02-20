# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - SQLAlchemy store.

Stores key/value pairs into any database supported by SQLAlchemy.
"""

from __future__ import annotations

import os

from typing import Any, BinaryIO, TYPE_CHECKING
from typing_extensions import override, Self

from io import BytesIO

from sqlalchemy import create_engine, select, MetaData, Table, Column, String, LargeBinary
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from moin.constants.namespaces import NAMESPACE_USERPROFILES
from moin.storage.error import StorageError

from . import BytesStoreBase, FileStoreBase

if TYPE_CHECKING:
    from sqlalchemy import Engine

KEY_LEN = 128
VALUE_LEN = 1024 * 1024  # 1MB binary data


class SQLAlchemyStoreMixin:

    @classmethod
    def from_uri(cls, uri: str) -> Self:
        """
        Create a new cls instance from the given URI.

        :param cls: Class to create.
        :param uri: The database URI that we pass on to SQLAlchemy.
        """
        # using "::" to support windows pathnames that may include ":" after the drive letter.
        params = uri.split("::")
        kwargs: dict[str, Any] = {}
        if len(params) > 0:
            kwargs["db_uri"] = params[0]
        if len(params) > 1:
            kwargs["table_name"] = params[1]
        if len(params) > 2:
            kwargs["verbose"] = params[2].lower() == "true"
        return cls(**kwargs)

    def __init__(self, db_uri: str | None = None, table_name: str = "store", verbose: bool = False) -> None:
        """
        :param db_uri: The database URI that we pass on to SQLAlchemy.
                       May contain user/password/host/port/etc.
        :param verbose: Verbosity setting. If set to True, this will print all SQL queries
                        to the console.
        """
        self.db_uri = db_uri
        self.verbose = verbose
        self.engine: Engine | None = None
        self.table: Table | None = None
        self.table_name = table_name
        self._make_dirs()

    def _make_dirs(self) -> None:
        if self.db_uri is None:
            return
        if self.db_uri.startswith("sqlite:///"):
            db_path = os.path.dirname(self.db_uri.split("sqlite:///")[1])
            if db_path and not os.path.exists(db_path):
                os.makedirs(db_path)

    def _engine(self) -> Engine:
        if self.engine is None:
            raise StorageError("SQLAlchemy store: no engine")
        return self.engine

    def open(self) -> None:
        if (db_uri := self.db_uri) is None:
            # These settings apply only for development/testing. The additional args are necessary
            # due to some limitations of the in-memory SQLite database.
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

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
        self.table = None

    def create(self) -> None:
        self.open()
        with self._engine().connect() as conn:
            with conn.begin():
                self.metadata.create_all(conn)
        self.close()

    def destroy(self):
        self.open()
        with self._engine().connect() as conn:
            with conn.begin():
                self.metadata.drop_all(conn)
        self.close()

    def __iter__(self):
        with self._engine().connect() as conn:
            rows = conn.execute(select(self.table.c.key))
            for row in rows:
                yield row[0]

    def __delitem__(self, key):
        with self._engine().connect() as conn:
            with conn.begin():
                conn.execute(self.table.delete().where(self.table.c.key == key))

    def _getitem(self, key):
        with self._engine().connect() as conn:
            value = conn.execute(select(self.table.c.value).where(self.table.c.key == key)).fetchone()
            if value is not None:
                return value[0]
            else:
                raise KeyError(key)

    def _setitem(self, key, value):
        with self._engine().connect() as conn:
            with conn.begin():
                try:
                    conn.execute(self.table.insert().values(key=key, value=value))
                except IntegrityError:
                    if NAMESPACE_USERPROFILES in self.db_uri:
                        # userprofiles namespace does support revisions so we update existing row
                        conn.execute(self.table.update().values(key=key, value=value))
                    else:
                        raise


class BytesStore(SQLAlchemyStoreMixin, BytesStoreBase):
    """
    A simple dict-based in-memory store. No persistence!
    """

    def __getitem__(self, key):
        return self._getitem(key)

    def __setitem__(self, key, value):
        self._setitem(key, value)


class FileStore(SQLAlchemyStoreMixin, FileStoreBase):
    """
    SQLAlchemy FileStore.
    """

    @override
    def __getitem__(self, key: str) -> BinaryIO:
        value = self._getitem(key)
        return BytesIO(value)

    @override
    def __setitem__(self, key: str, stream: BinaryIO) -> None:
        value = stream.read()
        self._setitem(key, value)
