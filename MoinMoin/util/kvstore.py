#!/usr/bin/env python
"""
kvstore - a flexible key/value store using sqlalchemy

@copyright: 2010 by Thomas Waldmann
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from UserDict import DictMixin

from sqlalchemy import MetaData, Table, Column
from sqlalchemy import Integer, String, Unicode, DateTime, PickleType, ForeignKey
from sqlalchemy import select
from sqlalchemy.sql import and_, exists


class KVStoreMeta(object):
    """
    Key/Value Store sqlalchemy metadata - defining DB tables and columns.
    """
    # for sqlite, lengths are not needed, but for other SQL DBs
    # for key_table we try to maybe have row length of 64 Bytes:
    TYPE_LEN = 16 # max. length of type names
    KEY_LEN = 64 - TYPE_LEN - 4 # max. length of key names
    # for value_table, we try to maybe have a row length of 4096 Bytes:
    VALUE_LEN = 4096-4 # max. length of values (used for str and unicode types)

    PICKLE_VALUE_TYPE = 'pickle'

    @classmethod
    def create_fact_table(cls, name, metadata, ref_type):
        """
        create a fact table that associates some outside item identified by
        ref_id (type ref_type) with a kvstore key/value pair identified byi
        key_id/value_id
        """
        return Table(name + '_fact', metadata,
            Column('ref_id', ref_type, primary_key=True), # ForeignKey into some table of user
            Column('key_id', ForeignKey('%s_key.id' % name), primary_key=True),
            Column('value_id', Integer, primary_key=True), # this is a ForeignKey into some value_table
        )

    @classmethod
    def create_key_table(cls, name, metadata):
        """
        create a key table that stores key names and value types (each key
        name is only paired with values of 1 specific type)
        """
        return Table(name + '_key', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(cls.KEY_LEN), index=True, unique=True),
            Column('value_type', String(cls.TYPE_LEN)), # key into value_tables
        )

    @classmethod
    def create_value_tables(cls, name, metadata):
        """
        create multiple value tables - each stores values of some specific type.
        we use one table (not: one column) per type to save some space.
        dict keys for value_tables are Python's __class__.__name__.
        """
        value_tables = {
            'unicode': Table(name + '_value_unicode', metadata,
                Column('id', Integer, primary_key=True),
                Column('value', Unicode(cls.VALUE_LEN), index=True),
            ),
            'str': Table(name + '_value_str', metadata,
                Column('id', Integer, primary_key=True),
                Column('value', String(cls.VALUE_LEN), index=True),
            ),
            'int': Table(name + '_value_int', metadata,
                Column('id', Integer, primary_key=True),
                Column('value', Integer, index=True),
            ),
            'datetime': Table(name + '_value_datetime', metadata,
                Column('id', Integer, primary_key=True),
                Column('value', DateTime, index=True),
            ),
            cls.PICKLE_VALUE_TYPE: Table(name + '_value_' + cls.PICKLE_VALUE_TYPE, metadata,
                Column('id', Integer, primary_key=True),
                Column('value', PickleType),
            ),
        }
        supported_value_types = [key for key in value_tables if key != cls.PICKLE_VALUE_TYPE]
        return value_tables, supported_value_types

    def __init__(self, name, metadata, ref_type):
        """
        Initialize the KV store metadata
        """
        self.name = name
        self.fact_table = self.create_fact_table(name, metadata, ref_type)
        self.key_table = self.create_key_table(name, metadata)
        self.value_tables, self.supported_value_types = self.create_value_tables(name, metadata)


class KVStore(object):
    """
    A flexible Key/Value store

    It can store arbitrary key names (unicode), new key names are added
    automatically.

    Each key name is associated with 1 value type, which is defined when first
    key/value pair is added to the store. See KVStoreMeta for details about
    value types.

    A key name is stored only once and referred to by its key_id primary key.
    A value is stored only once and referred to by its value_id primary key.

    When retrieving key/value pairs, you just give the same reference id
    (ref_id) that you used for storing those key/value pairs that belong to
    that reference id.
    """
    def __init__(self, meta):
        # note: for ease of use, we use implicit execution. it requires that
        # you have bound an engine to the metadata: metadata.bind = engine
        self.fact_table = meta.fact_table
        self.key_table = meta.key_table
        self.value_tables = meta.value_tables
        self.supported_value_types = meta.supported_value_types
        self.PICKLE_VALUE_TYPE = meta.PICKLE_VALUE_TYPE

    def _get_value_type(self, value):
        """
        get the type string we use for this value.

        For directly supported value types, it is the python class name,
        otherwise we use pickle.
        """
        value_type = value.__class__.__name__
        if value_type not in self.supported_value_types:
            value_type = self.PICKLE_VALUE_TYPE
        return value_type

    def _get_key_id(self, name, value):
        """
        get key_id for <name> (create new entry for <name> if there is none yet)
        """
        key_table = self.key_table
        name = unicode(name)
        value_type = self._get_value_type(value)
        result = select([key_table.c.id, key_table.c.value_type],
                        key_table.c.name == name
                       ).execute().fetchone()
        if result:
            key_id, wanted_value_type = result
            assert wanted_value_type == value_type, "wanted: %r have: %r name: %r value: %r" % (
                   wanted_value_type, value_type, name, value)
        else:
            res = key_table.insert().values(name=name, value_type=value_type).execute()
            key_id = res.inserted_primary_key[0]
        return key_id

    def _get_value_id(self, value):
        """
        get value_id for value (create new entry for <value> if there is none yet)
        """
        value_type = self._get_value_type(value)
        value_table = self.value_tables[value_type]
        result = select([value_table.c.id],
                        value_table.c.value == value
                       ).execute().fetchone()
        if result:
            value_id = result[0]
        else:
            res = value_table.insert().values(value=value).execute()
            value_id = res.inserted_primary_key[0]
        return value_id

    def _associate(self, ref_id, key_id, value_id):
        """
        associate a k/v pair identified by (key_id, value_id) with some entity identified by ref_id
        """
        fact_table = self.fact_table
        result = select(['*'],
                        and_(fact_table.c.ref_id == ref_id,
                             fact_table.c.key_id == key_id)
                       ).execute().fetchone()
        if result:
            res = fact_table.update().where(
                      and_(fact_table.c.ref_id == ref_id,
                           fact_table.c.key_id == key_id)
                  ).values(value_id=value_id).execute()
        else:
            res = fact_table.insert().values(ref_id=ref_id, key_id=key_id, value_id=value_id).execute()

    def _unassociate_all(self, ref_id):
        """
        unassociate all k/v pairs that are associated with some entity identified by ref_id
        """
        fact_table = self.fact_table
        fact_table.delete().where(fact_table.c.ref_id == ref_id).execute()

    def store(self, ref_id, name, value):
        """
        store a pair name:value and associate it with ref_id
        """
        key_id = self._get_key_id(name, value)
        value_id = self._get_value_id(value)
        self._associate(ref_id, key_id, value_id)

    def retrieve(self, ref_id, name):
        """
        retrieve a value of a name:value pair associated with ref_id
        """
        fact_table = self.fact_table
        key_table = self.key_table
        value_tables = self.value_tables
        name = unicode(name)
        value_type, value_id = select([key_table.c.value_type, fact_table.c.value_id],
                                      and_(fact_table.c.ref_id == ref_id,
                                           fact_table.c.key_id == key_table.c.id,
                                           key_table.c.name == name)
                                     ).execute().fetchone()
        value_table = value_tables[value_type]
        value = select([value_table.c.value],
                       value_table.c.id == value_id
                      ).execute().fetchone()[0]
        return value

    def store_kv(self, ref_id, kvs):
        """
        store k/v pairs from kvs dict and associate them with ref_id
        """
        self._unassociate_all(ref_id)
        for k, v in kvs.items():
            self.store(ref_id, k, v)

    def retrieve_kv(self, ref_id):
        """
        get all k/v pairs associated with ref_id
        """
        fact_table = self.fact_table
        key_table = self.key_table
        value_tables = self.value_tables
        results = select([key_table.c.name, key_table.c.value_type, fact_table.c.value_id],
                         and_(fact_table.c.ref_id == ref_id,
                              fact_table.c.key_id == key_table.c.id)
                        ).execute().fetchall()
        result_dict = {}
        for name, value_type, value_id in results:
            value_table = value_tables[value_type]
            value = select([value_table.c.value],
                           value_table.c.id == value_id
                          ).execute().fetchone()[0]
            result_dict[name] = value
        return result_dict

    def has_kv(self, ref_table, **kvs):
        """
        return a conditional that can be used to select ref_table entries that
        have all given k/v pairs associated with them
        """
        fact_table = self.fact_table
        key_table = self.key_table
        value_tables = self.value_tables
        terms = []
        for name, value in kvs.items():
            name = unicode(name)
            value_type = self._get_value_type(value)
            # XXX does the comparison below work for pickle?
            value_table = value_tables[value_type]
            terms.append(exists().where(and_(
                  key_table.c.name == name,
                  value_table.c.value == value,
                  fact_table.c.key_id == key_table.c.id,
                  fact_table.c.value_id == value_table.c.id,
                  ref_table.c.id == fact_table.c.ref_id)))
        return and_(*terms)


class KVItem(object, DictMixin):
    """
    Provides dict-like access to key/values related to one item referenced
    by ref_id that is stored in a KVStore.
    """
    def __init__(self, kvstore, ref_id):
        self.kvstore = kvstore
        self.ref_id = ref_id

    def __getitem__(self, name):
        return self.kvstore.retrieve(self.ref_id, name)

    def __setitem__(self, name, value):
        self.kvstore.store(self.ref_id, name, value)


