# Copyright: 2010-2011 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Indexing Mixin Classes

    Other backends mix in the Indexing*Mixin classes into their Backend,
    Item, Revision classes to support flexible metadata indexing and querying
    for wiki items / revisions

    Wiki items and revisions of same item are identified by same UUID.
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
from MoinMoin.converter import convert_to_indexable

from MoinMoin import log
logging = log.getLogger(__name__)

class IndexingBackendMixin(object):
    """
    Backend indexing support
    """
    def __init__(self, *args, **kw):
        cfg = kw.pop('cfg', None)
        super(IndexingBackendMixin, self).__init__(*args, **kw)
        self._index = ItemIndex(cfg)

    def close(self):
        self._index.close()
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
        for result in self._index.history(reverse=reverse, item_name=item_name, start=start, end=end):
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
        return self._index.all_tags()

    def tagged_items(self, tag):
        """
        Return a list of item names of items that are tagged with <tag>.
        """
        return self._index.tagged_items(tag)


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

    def remove_index(self):
        """
        update the index, removing everything related to this revision
        """
        name = self.item.name
        uuid = self.item[UUID]
        revno = self.revno
        metas = self
        logging.debug("item %r revno %d remove index!" % (name, revno))
        self._index.remove_rev(metas[UUID], revno)

    # TODO maybe use this class later for data indexing also,
    # TODO by intercepting write() to index data written to a revision


from whoosh.writing import AsyncWriter
from MoinMoin.search.indexing import WhooshIndex

class ItemIndex(object):
    """
    Index for Items/Revisions
    """
    def __init__(self, cfg):
        self.wikiname = cfg.interwikiname or u''
        self.index_object = WhooshIndex(cfg=cfg)

    def close(self):
        self.index_object.all_revisions_index.close()
        self.index_object.latest_revisions_index.close()

    def index_rebuild(self, backend):
        # do we need a whoosh implementation of this?
        pass

    def update_item(self, metas):
        """
        update item (not revision!) metadata
        """
        return
        # XXX wrong, this is for item level metadata, not revision metadata!
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            doc_number = latest_revs_searcher.document_number(uuid=metas[UUID],
                                                              wikiname=self.wikiname
                                                             )
        with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
            if doc_number:
                async_writer.delete_document(doc_number)
            async_writer.add_document(**metas)

    def remove_item(self, metas):
        """
        remove item (not revision!) metadata
        """
        return
        # XXX wrong, this is for item level metadata, not revision metadata!
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            doc_number = latest_revs_searcher.document_number(uuid=metas[UUID],
                                                              name_exact=metas[NAME],
                                                              wikiname=self.wikiname
                                                             )
        if doc_number is not None:
            with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
                async_writer.delete_document(doc_number)

    def add_rev(self, uuid, revno, rev):
        """
        add a new revision <revno> for item <uuid> with metadata <metas>
        """
        with self.index_object.all_revisions_index.searcher() as all_revs_searcher:
            all_found_document = all_revs_searcher.document(uuid=rev[UUID],
                                                            rev_no=revno,
                                                            wikiname=self.wikiname
                                                           )
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            latest_found_document = latest_revs_searcher.document(uuid=rev[UUID],
                                                                  wikiname=self.wikiname
                                                                 )
        logging.debug("Processing: name %s revno %s" % (rev[NAME], revno))
        rev.seek(0) # for a new revision, file pointer points to EOF, rewind first
        rev_content = convert_to_indexable(rev)
        logging.debug("Indexable content: %r" % (rev_content[:250], ))
        if not all_found_document:
            field_names = self.index_object.all_revisions_index.schema.names()
            with AsyncWriter(self.index_object.all_revisions_index) as async_writer:
                converted_rev = backend_to_index(rev, revno, field_names, rev_content, self.wikiname)
                logging.debug("All revisions: adding %s %s", converted_rev[NAME], converted_rev["rev_no"])
                async_writer.add_document(**converted_rev)
        if not latest_found_document or int(revno) > latest_found_document["rev_no"]:
            field_names = self.index_object.latest_revisions_index.schema.names()
            with AsyncWriter(self.index_object.latest_revisions_index) as async_writer:
                converted_rev = backend_to_index(rev, revno, field_names, rev_content, self.wikiname)
                logging.debug("Latest revisions: updating %s %s", converted_rev[NAME], converted_rev["rev_no"])
                async_writer.update_document(**converted_rev)

    def remove_rev(self, uuid, revno):
        """
        remove a revision <revno> of item <uuid>
        """
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

    def history(self, mountpoint=u'', item_name=u'', reverse=True, start=None, end=None):
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
        with self.index_object.latest_revisions_index.searcher() as latest_revs_searcher:
            docs = latest_revs_searcher.documents(tags=tag, wikiname=self.wikiname)
            return [doc[NAME] for doc in docs]

