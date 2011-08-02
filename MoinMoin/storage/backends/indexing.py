# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Indexing Mixin Classes

    Other backends mix in the Indexing*Mixin classes into their Backend,
    Item, Revision classes to support flexible metadata indexing and querying
    for wiki items / revisions

    Wiki items are identified by a UUID (in the index, it is internally mapped
    to an integer for more efficient processing).
    Revisions of an item are identified by a integer revision number (and the
    parent item).

    The wiki item name is contained in the item revision's metadata.
    If you rename an item, this is done by creating a new revision with a different
    (new) name in its revision metadata.
"""


import os
import time, datetime

from uuid import uuid4
make_uuid = lambda: unicode(uuid4().hex)

from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   AccessDeniedError
from MoinMoin.config import ACL, CONTENTTYPE, UUID, NAME, NAME_OLD, MTIME, TAGS
from MoinMoin.search.revision_converter import backend_to_index

from MoinMoin import log
logging = log.getLogger(__name__)

class IndexingBackendMixin(object):
    """
    Backend indexing support
    """
    def __init__(self, *args, **kw):
        index_uri = kw.pop('index_uri', None)
        cfg = kw.pop('cfg', None)
        super(IndexingBackendMixin, self).__init__(*args, **kw)
        self._index = ItemIndex(index_uri, cfg)

    def close(self):
        self._index.close()
        self._index.close_whoosh()
        super(IndexingBackendMixin, self).close()

    def create_item(self, itemname):
        """
        intercept new item creation and make sure there is NAME / UUID in the item
        """
        item = super(IndexingBackendMixin, self).create_item(itemname)
        item.change_metadata()
        if NAME not in item:
            item[NAME] = itemname
        if UUID not in item:
            item[UUID] = make_uuid()
        item.publish_metadata()
        return item

    def index_rebuild(self):
        return self._index.index_rebuild(self)

    def history(self, reverse=True, item_name=u'', start=None, end=None):
        """
        History implementation using the index.
        """
        for result in self._index.history_whoosh(reverse=reverse, item_name=item_name, start=start, end=end):
            # we currently create the item, the revision and yield it to stay
            # compatible with storage api definition, but this could be changed to
            # just return the data we get from the index (without accessing backend)
            # TODO: A problem exists at item = self.get_item(name).
            # In the history_size_after_rename test in test_backends.py,
            # an item was created with the name "first" and then renamed to "second."
            # When it runs through this history function and runs item = self.get_item("first"),
            # it can't find it because it was already renamed to "second."
            # Some suggested solutions are: using some neverchanging uuid to identify some specific item
            # or continuing to use the name, but tracking name changes within the item's history.
            rev_datetime, name, rev_no = result
            try:
                logging.debug("HISTORY: name %s revno %s" % (name, rev_no))
                item = self.get_item(name)
                yield item.get_revision(rev_no)
            except AccessDeniedError as e:
                # just skip items we may not access
                pass
            except (NoSuchItemError, NoSuchRevisionError) as e:
                logging.exception("history processing catched exception")

    def all_tags(self):
        """
        Return a unsorted list of tuples (count, tag, tagged_itemnames) for all
        tags.
        """
        return self._index.all_tags_whoosh()

    def tagged_items(self, tag):
        """
        Return a list of item names of items that are tagged with <tag>.
        """
        return self._index.tagged_items_whoosh(tag)


class IndexingItemMixin(object):
    """
    Item indexing support

    When a commit happens, index stuff.
    """
    def __init__(self, backend, *args, **kw):
        super(IndexingItemMixin, self).__init__(backend, *args, **kw)
        self._index = backend._index
        self.__unindexed_revision = None

    def create_revision(self, revno):
        self.__unindexed_revision = super(IndexingItemMixin, self).create_revision(revno)
        return self.__unindexed_revision

    def commit(self):
        self.__unindexed_revision.update_index()
        self.__unindexed_revision = None
        return super(IndexingItemMixin, self).commit()

    def rollback(self):
        self.__unindexed_revision = None
        return super(IndexingItemMixin, self).rollback()

    def publish_metadata(self):
        self.update_index()
        return super(IndexingItemMixin, self).publish_metadata()

    def destroy(self):
        self.remove_index()
        return super(IndexingItemMixin, self).destroy()

    def update_index(self):
        """
        update the index with metadata of this item

        this is automatically called by item.publish_metadata() and can be used by a indexer script also.
        """
        logging.debug("item %r update index:" % (self.name, ))
        for k, v in self.items():
            logging.debug(" * item meta %r: %r" % (k, v))
        self._index.update_item(metas=self)

    def remove_index(self):
        """
        update the index, removing everything related to this item
        """
        logging.debug("item %r remove index!" % (self.name, ))
        self._index.remove_item(metas=self)


class IndexingRevisionMixin(object):
    """
    Revision indexing support
    """
    def __init__(self, item, *args, **kw):
        super(IndexingRevisionMixin, self).__init__(item, *args, **kw)
        self._index = item._index

    def destroy(self):
        self.remove_index()
        return super(IndexingRevisionMixin, self).destroy()

    def update_index(self):
        """
        update the index with metadata of this revision

        this is automatically called by item.commit() and can be used by a indexer script also.
        """
        name = self.item.name
        uuid = self.item[UUID]
        revno = self.revno
        if MTIME not in self:
            self[MTIME] = int(time.time())
        if NAME not in self:
            self[NAME] = name
        if UUID not in self:
            self[UUID] = uuid # do we want the item's uuid in the rev's metadata?
        if CONTENTTYPE not in self:
            self[CONTENTTYPE] = 'application/octet-stream'
        metas = self
        logging.debug("item %r revno %d update index:" % (name, revno))
        for k, v in metas.items():
            logging.debug(" * rev meta %r: %r" % (k, v))
        self._index.add_rev(uuid, revno, metas)
        self._index.add_rev_whoosh(uuid, revno, metas)

    def remove_index(self):
        """
        update the index, removing everything related to this revision
        """
        name = self.item.name
        uuid = self.item[UUID]
        revno = self.revno
        metas = self
        logging.debug("item %r revno %d remove index!" % (name, revno))
        self._index.remove_rev(uuid, revno)
        self._index.remove_rev_whoosh(metas[UUID], revno)

    # TODO maybe use this class later for data indexing also,
    # TODO by intercepting write() to index data written to a revision

from MoinMoin.util.kvstore import KVStoreMeta, KVStore

from sqlalchemy import Table, Column, Integer, String, Unicode, DateTime, PickleType, MetaData, ForeignKey
from sqlalchemy import create_engine, select
from sqlalchemy.sql import and_, exists, asc, desc

from whoosh.writing import AsyncWriter
from MoinMoin.search.indexing import WhooshIndex

class ItemIndex(object):
    """
    Index for Items/Revisions
    """
    def __init__(self, index_uri, cfg):
        metadata = MetaData()
        metadata.bind = create_engine(index_uri, echo=False)

        # for sqlite, lengths are not needed, but for other SQL DBs:
        UUID_LEN = 32
        VALUE_LEN = KVStoreMeta.VALUE_LEN # we duplicate values from there to our table

        # items have a persistent uuid
        self.item_table = Table('item_table', metadata,
            Column('id', Integer, primary_key=True), # item's internal uuid
            # reference to current revision:
            Column('current', ForeignKey('rev_table.id', name="current", use_alter=True), type_=Integer),
            # some important stuff duplicated here for easy availability:
            # from item metadata:
            Column('uuid', String(UUID_LEN), index=True, unique=True), # item's official persistent uuid
            # from current revision's metadata:
            Column('name', Unicode(VALUE_LEN), index=True, unique=True),
            Column('contenttype', Unicode(VALUE_LEN), index=True),
            Column('acl', Unicode(VALUE_LEN)),
            Column('tags', Unicode(VALUE_LEN)),
        )

        # revisions have a revno and a parent item
        self.rev_table = Table('rev_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('item_id', ForeignKey('item_table.id')),
            Column('revno', Integer),
            # some important stuff duplicated here for easy availability:
            Column('datetime', DateTime, index=True),
        )

        item_kvmeta = KVStoreMeta('item', metadata, Integer)
        rev_kvmeta = KVStoreMeta('rev', metadata, Integer)
        metadata.create_all()
        self.metadata = metadata
        self.item_kvstore = KVStore(item_kvmeta)
        self.rev_kvstore = KVStore(rev_kvmeta)

        self.wikiname = cfg.interwikiname or u''
        self.index_object = WhooshIndex(cfg=cfg)

    def close(self):
        engine = self.metadata.bind
        engine.dispose()

    def close_whoosh(self):
        self.index_object.all_revisions_index.close()
        self.index_object.latest_revisions_index.close()

    def index_rebuild(self, backend):
        self.metadata.drop_all()
        self.metadata.create_all()
        for item in backend.iter_items_noindex():
            item.update_index()
            for revno in item.list_revisions():
                rev = item.get_revision(revno)
                logging.debug("rebuild %s %d" % (rev[NAME], revno))
                rev.update_index()

    def get_item_id(self, uuid):
        """
        return the internal item id for some item with uuid or
        None, if not found.
        """
        item_table = self.item_table
        result = select([item_table.c.id],
                        item_table.c.uuid == uuid
                       ).execute().fetchone()
        if result:
            return result[0]

    def get_item_id_whoosh(self, uuid):
        with self.index_object.latest_revisions_index.searcher() as searcher:
            result = searcher.document(uuid=uuid, wikiname=self.wikiname)
        if result:
            return result

    def update_item(self, metas):
        """
        update an item with item-level metadata <metas>

        note: if item does not exist already, it is added
        """
        name = metas.get(NAME, '') # item name (if revisioned: same as current revision's name)
        uuid = metas.get(UUID, '') # item uuid (never changes)
        item_table = self.item_table
        item_id = self.get_item_id(uuid)
        if item_id is None:
            res = item_table.insert().values(uuid=uuid, name=name).execute()
            item_id = res.inserted_primary_key[0]
        self.item_kvstore.store_kv(item_id, metas)
        return item_id

    def update_item_whoosh(self, metas):
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            doc_number = latest_revs_searcher.document_number(uuid=metas[UUID],
                                                              wikiname=self.wikiname
                                                             )
        with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
            if doc_number:
                async_writer.delete_document(doc_number)
            async_writer.add_document(**metas)

    def cache_in_item(self, item_id, rev_id, rev_metas):
        """
        cache some important values from current revision into item for easy availability
        """
        item_table = self.item_table
        item_table.update().where(item_table.c.id == item_id).values(
            current=rev_id,
            name=rev_metas[NAME],
            contenttype=rev_metas[CONTENTTYPE],
            acl=rev_metas.get(ACL, ''),
            tags=u'|' + u'|'.join(rev_metas.get(TAGS, [])) + u'|',
        ).execute()

    def remove_item(self, metas):
        """
        remove an item

        note: does not remove revisions, these should be removed first
        """
        item_table = self.item_table
        name = metas.get(NAME, '') # item name (if revisioned: same as current revision's name)
        uuid = metas.get(UUID, '') # item uuid (never changes)
        item_id = self.get_item_id(uuid)
        if item_id is not None:
            self.item_kvstore.store_kv(item_id, {})
            item_table.delete().where(item_table.c.id == item_id).execute()

    def remove_item_whoosh(self, metas):
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            doc_number = latest_revs_searcher.document_number(uuid=metas[UUID],
                                                              name_exact=metas[NAME],
                                                              wikiname=self.wikiname
                                                             )
        if doc_number is not None:
            with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
                async_writer.delete_document(doc_number)

    def add_rev(self, uuid, revno, metas):
        """
        add a new revision <revno> for item <uuid> with metadata <metas>

        currently assumes that added revision will be latest/current revision (not older/non-current)
        """
        rev_table = self.rev_table
        item_metas = dict(uuid=uuid, name=metas[NAME])
        item_id = self.update_item(item_metas)

        # get (or create) the revision entry
        result = select([rev_table.c.id],
                        and_(rev_table.c.revno == revno,
                             rev_table.c.item_id == item_id)
                       ).execute().fetchone()
        if result:
            rev_id = result[0]
        else:
            dt = datetime.datetime.utcfromtimestamp(metas[MTIME])
            res = rev_table.insert().values(revno=revno, item_id=item_id, datetime=dt).execute()
            rev_id = res.inserted_primary_key[0]

        self.rev_kvstore.store_kv(rev_id, metas)

        self.cache_in_item(item_id, rev_id, metas)
        return rev_id

    def add_rev_whoosh(self, uuid, revno, metas):
        with self.index_object.all_revisions_index.searcher() as all_revs_searcher:
            all_found_document = all_revs_searcher.document(uuid=metas[UUID],
                                                            rev_no=revno,
                                                            wikiname=self.wikiname
                                                           )
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            latest_found_document = latest_revs_searcher.document(uuid=metas[UUID],
                                                                  wikiname=self.wikiname
                                                                 )
        logging.debug("To add: uuid %s revno %s" % (metas[UUID], revno))
        if not all_found_document:
            field_names = self.index_object.all_revisions_index.schema.names()
            with AsyncWriter(self.index_object.all_revisions_index) as async_writer:
                converted_rev = backend_to_index(metas, revno, field_names, self.wikiname)
                logging.debug("ALL: add %s %s", converted_rev[UUID], converted_rev["rev_no"])
                async_writer.add_document(**converted_rev)
        if not latest_found_document or int(revno) > latest_found_document["rev_no"]:
            field_names = self.index_object.latest_revisions_index.schema.names()
            with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
                logging.debug("LATEST: Updating %s %s from last", converted_rev[UUID], converted_rev["rev_no"])
                async_writer.update_document(**converted_rev)

    def remove_rev(self, uuid, revno):
        """
        remove a revision <revno> of item <uuid>

        Note:

        * does not update metadata values cached in item (this is only a
          problem if you delete latest revision AND you don't delete the
          whole item anyway)
        """
        item_id = self.get_item_id(uuid)
        assert item_id is not None

        # get the revision entry
        rev_table = self.rev_table
        result = select([rev_table.c.id],
                        and_(rev_table.c.revno == revno,
                             rev_table.c.item_id == item_id)
                       ).execute().fetchone()
        if result:
            rev_id = result[0]
            self.rev_kvstore.store_kv(rev_id, {})
            rev_table.delete().where(rev_table.c.id == rev_id).execute()

    def remove_rev_whoosh(self, uuid, revno):
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            latest_doc_number = latest_revs_searcher.document_number(uuid=uuid,
                                                                     rev_no=revno,
                                                                     wikiname=self.wikiname
                                                                    )
        with self.index_object.all_revisions_index.searcher() as all_revs_searcher:
            doc_number = all_revs_searcher.document_number(uuid=uuid,
                                                           rev_no=revno,
                                                           wikiname=self.wikiname
                                                          )
        if doc_number is not None:
            with AsyncWriter(self.index_object.all_revisions_index) as async_writer:
                logging.debug("REMOVE FROM ALL: %d", doc_number)
                async_writer.delete_document(doc_number)
        if latest_doc_number is not None:
            with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
                logging.debug("REMOVE FROM LATEST: %d", latest_doc_number)
                async_writer.delete_document(latest_doc_number)

    def get_uuid_revno_name(self, rev_id):
        """
        get item uuid and revision number by rev_id
        """
        item_table = self.item_table
        rev_table = self.rev_table
        result = select([item_table.c.uuid, rev_table.c.revno, item_table.c.name],
                        and_(rev_table.c.id == rev_id,
                             item_table.c.id == rev_table.c.item_id)
                       ).execute().fetchone()
        return result

    def history(self, mountpoint=u'', item_name=u'', reverse=True, start=None, end=None):
        """
        Yield ready-to-use history raw data for this backend.
        """
        if mountpoint:
            mountpoint += '/'

        item_table = self.item_table
        rev_table = self.rev_table

        selection = [rev_table.c.datetime, item_table.c.name, rev_table.c.revno, rev_table.c.id, ]

        if reverse:
            order_attr = desc(rev_table.c.datetime)
        else:
            order_attr = asc(rev_table.c.datetime)

        if not item_name:
            # empty item_name = all items
            condition = item_table.c.id == rev_table.c.item_id
        else:
            condition = and_(item_table.c.id == rev_table.c.item_id,
                             item_table.c.name == item_name)

        query = select(selection, condition).order_by(order_attr)
        if start is not None:
            query = query.offset(start)
            if end is not None:
                query = query.limit(end-start)

        for rev_datetime, name, revno, rev_id in query.execute().fetchall():
            rev_metas = self.rev_kvstore.retrieve_kv(rev_id)
            yield (rev_datetime, mountpoint + name, revno, rev_metas)

    def history_whoosh(self, mountpoint=u'', item_name=u'', reverse=True, start=None, end=None):
        if mountpoint:
            mountpoint += '/'
        with self.index_object.all_revisions_index.searcher() as all_revs_searcher:
            if item_name:
                docs = all_revs_searcher.documents(name_exact=item_name,
                                                   wikiname=self.wikiname
                                                  )
            else:
                docs = all_revs_searcher.documents(wikiname=self.wikiname)
            for doc in sorted(docs, reverse=reverse)[start:end]:
                yield (doc[MTIME], mountpoint + doc[NAME], doc["rev_no"])

    def all_tags(self):
        item_table = self.item_table
        result = select([item_table.c.name, item_table.c.tags],
                        item_table.c.tags != u'||').execute().fetchall()
        tags_names = {}
        for name, tags in result:
            for tag in tags.split(u'|')[1:-1]:
                tags_names.setdefault(tag, []).append(name)
        counts_tags_names = [(len(names), tag, names) for tag, names in tags_names.items()]
        return counts_tags_names

    def all_tags_whoosh(self):
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            docs = latest_revs_searcher.documents(wikiname=self.wikiname)
            tags_names = {}
            for doc in docs:
                tags = doc.get(TAGS, [])
                logging.debug("name %s rev %s tags %s" % (doc[NAME], doc["rev_no"], tags))
                for tag in tags:
                    tags_names.setdefault(tag, []).append(doc[NAME])
            counts_tags_names = [(len(names), tag, names) for tag, names in tags_names.items()]
            return counts_tags_names

    def tagged_items(self, tag):
        item_table = self.item_table
        result = select([item_table.c.name],
                        item_table.c.tags.like('%%|%s|%%' % tag)).execute().fetchall()
        return [row[0] for row in result]

    def tagged_items_whoosh(self, tag):
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            docs = latest_revs_searcher.documents(tags=tag, wikiname=self.wikiname)
            return [doc[NAME] for doc in docs]
