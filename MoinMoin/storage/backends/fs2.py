# Copyright: 2008 MoinMoin:JohannesBerg ("fs2" is originally based on "fs" from JB)
# Copyright: 2009-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - FS2 backend

    Features:
    * store metadata and data separately
    * use uuids for item storage names
    * uses content hash addressing for revision data storage
    * use sqlalchemy/sqlite (not cdb/self-made DBs like fs does)
"""


import os, tempfile, errno, shutil
from uuid import uuid4 as make_uuid

import cPickle as pickle

from flask import current_app as app

from sqlalchemy import create_engine, MetaData, Table, Column, String, Unicode, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from werkzeug import cached_property

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.util.lock import ExclusiveLock
from MoinMoin.util import filesys

from MoinMoin.storage import Backend as BackendBase
from MoinMoin.storage import Item as ItemBase
from MoinMoin.storage import StoredRevision as StoredRevisionBase
from MoinMoin.storage import NewRevision as NewRevisionBase

from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError, \
                                   CouldNotDestroyError

PICKLEPROTOCOL = 1

MAX_NAME_LEN = 500
from MoinMoin.config import HASH_ALGORITHM

UUID_LEN = len(make_uuid().hex)


class Item(ItemBase):
    def __init__(self, backend, item_name, _fs_item_id=None, _fs_metadata=None, *args, **kw):
        self._fs_item_id = _fs_item_id
        self._fs_metadata = _fs_metadata
        super(Item, self).__init__(backend, item_name, *args, **kw)


class StoredRevision(StoredRevisionBase):
    def __init__(self, item, revno, *args, **kw):
        self._fs_file_data = None
        if revno == -1:
            revs = item.list_revisions()
            if not revs:
                raise NoSuchRevisionError("Item '%r' has no revisions." % (item.name, ))
            revno = max(revs)
        super(StoredRevision, self).__init__(item, revno, *args, **kw)
        # fail early if we don't have such a revision:
        self._fs_path_meta = self._backend._make_path('meta', item._fs_item_id, '%d.rev' % revno)
        if not os.path.exists(self._fs_path_meta):
            raise NoSuchRevisionError("Item '%r' has no revision #%d." % (item.name, revno))

    @cached_property
    def _fs_metadata(self):
        with open(self._fs_path_meta, 'rb') as f:
            try:
                metadata = pickle.load(f)
            except EOFError:
                metadata = {}
        return metadata

    @cached_property
    def _fs_path_data(self):
        data_hash = self._fs_metadata[HASH_ALGORITHM]
        return self._backend._make_path('data', data_hash)


class NewRevision(NewRevisionBase):
    def __init__(self, item, revno, *args, **kw):
        super(NewRevision, self).__init__(item, revno, *args, **kw)
        def maketemp(kind):
            tmp_dir = self._backend._make_path(kind)
            fd, tmp_path = tempfile.mkstemp('.tmp', '', tmp_dir)
            tmp_file = os.fdopen(fd, 'wb') # XXX keeps file open as long a rev exists
            return tmp_file, tmp_path

        self._fs_file_meta, self._fs_path_meta = maketemp('meta')
        self._fs_file_data, self._fs_path_data = maketemp('data')


class FS2Backend(BackendBase):
    """
    FS2 backend
    """
    def __init__(self, path):
        """
        Initialise filesystem backend, creating initial files and some internal structures.

        :param path: storage path
        """
        self._path = path

        # create <path>, meta data and revision content data storage subdirs
        meta_path = self._make_path('meta')
        data_path = self._make_path('data')
        for path in (self._path, meta_path, data_path):
            try:
                os.makedirs(path)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise BackendError(str(err))

        engine = create_engine('sqlite:///%s' % self._make_path('index.db'), poolclass=NullPool, echo=False)
        metadata = MetaData()
        metadata.bind = engine

        # item_name -> item_id mapping
        self._name2id = Table('name2id', metadata,
                            Column('item_name', Unicode(MAX_NAME_LEN), primary_key=True),
                            Column('item_id', String(UUID_LEN), index=True, unique=True),
                        )

        metadata.create_all()

    def close(self):
        engine = self._name2id.metadata.bind
        engine.dispose()

    def _make_path(self, *args):
        return os.path.join(self._path, *args)

    def _get_item_id(self, itemname):
        """
        Get ID of item (or None if no such item exists)

        :param itemname: name of item (unicode)
        """
        name2id = self._name2id
        results = name2id.select(name2id.c.item_name==itemname).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            item_id = row[name2id.c.item_id]
            item_id = str(item_id) # we get unicode
            return item_id

    def _get_item_name(self, itemid):
        """
        Get name of item (or None if no such item exists)

        :param itemid: id of item (str)
        """
        name2id = self._name2id
        results = name2id.select(name2id.c.item_id==itemid).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            item_name = row[name2id.c.item_name]
            return item_name

    def get_item(self, itemname):
        item_id = self._get_item_id(itemname)
        if item_id is None:
            raise NoSuchItemError("No such item '%r'." % itemname)

        return Item(self, itemname, _fs_item_id=item_id)

    def has_item(self, itemname):
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must be of str/unicode type, not %s." % type(itemname))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An item '%r' already exists!" % itemname)

        return Item(self, itemname, _fs_metadata={})

    def iter_items_noindex(self):
        name2id = self._name2id
        results = name2id.select().execute()
        for row in results:
            item_name = row[name2id.c.item_name]
            item_id = row[name2id.c.item_id]
            item_id = str(item_id) # we get unicode!
            item = Item(self, item_name, _fs_item_id=item_id)
            yield item
        results.close()

    iteritems = iter_items_noindex

    def _get_revision(self, item, revno):
        return StoredRevision(item, revno)

    def _list_revisions(self, item):
        if item._fs_item_id is None:
            return []
        p = self._make_path('meta', item._fs_item_id)
        l = os.listdir(p)
        suffix = '.rev'
        ret = sorted([int(i[:-len(suffix)]) for i in l if i.endswith(suffix)])
        return ret

    def _create_revision(self, item, revno):
        if item._fs_item_id is None:
            revs = []
        else:
            revs = self._list_revisions(item)
        last_rev = max(-1, -1, *revs)

        if revno in revs:
            raise RevisionAlreadyExistsError("Item '%r' already has a revision #%d." % (item.name, revno))
        elif revno != last_rev + 1:
            raise RevisionNumberMismatchError("The latest revision of the item '%r' is #%d, thus you cannot create revision #%d. \
                                               The revision number must be latest_revision + 1." % (item.name, last_rev, revno))

        return NewRevision(item, revno)

    def _destroy_revision(self, rev):
        self._close_revision_data(rev)
        try:
            os.unlink(rev._fs_path_meta)
            # XXX do refcount data files and if zero, kill it
            #os.unlink(rev._fs_path_data)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy revision #%d of item '%r' [errno: %d]" % (
                    rev.revno, rev.item.name, err.errno))
            #else:
            #    someone else already killed this revision, we silently ignore this error

    def _do_locked(self, lockname, fn, arg):
        l = ExclusiveLock(lockname, 30)
        l.acquire(30)
        try:
            ret = fn(arg)
        finally:
            l.release()

        return ret

    def _rename_item_locked(self, arg):
        item, newname = arg
        item_id = item._fs_item_id

        name2id = self._name2id
        try:
            results = name2id.update().where(name2id.c.item_id==item_id).values(item_name=newname).execute()
            results.close()
        except IntegrityError:
            raise ItemAlreadyExistsError("Target item '%r' already exists!" % newname)

    def _rename_item(self, item, newname):
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._rename_item_locked, (item, newname))

    def _add_item_internally_locked(self, arg):
        """
        See _add_item_internally, this is just internal for locked operation.
        """
        item, revmeta, revdata, revdata_target, itemmeta = arg
        item_id = make_uuid().hex
        item_name = item.name

        name2id = self._name2id
        try:
            results = name2id.insert().values(item_id=item_id, item_name=item_name).execute()
            results.close()
        except IntegrityError:
            raise ItemAlreadyExistsError("Item '%r' already exists!" % item_name)

        os.mkdir(self._make_path('meta', item_id))

        if revdata is not None:
            filesys.rename(revdata, revdata_target)

        if revmeta is not None:
            rp = self._make_path('meta', item_id, '%d.rev' % 0)
            filesys.rename(revmeta, rp)

        if itemmeta:
            # only write item level metadata file if we have any
            mp = self._make_path('meta', item_id, 'item')
            with open(mp, 'wb') as f:
                pickle.dump(itemmeta, f, protocol=PICKLEPROTOCOL)

        item._fs_item_id = item_id

    def _add_item_internally(self, item, revmeta=None, revdata=None, revdata_target=None, itemmeta=None):
        """
        This method adds a new item. It locks the name-mapping database to
        ensure putting the item into place and adding it to the name-mapping
        db is atomic.

        If the newrev or metadata arguments are given, then it also adds the
        revision or metadata to the item before making it discoverable.

        If the item's name already exists, it doesn't do anything but raise
        a ItemAlreadyExistsError; if the newrev was given the file is unlinked.

        :param revmeta: new revision's temporary meta file path
        :param revdata: new revision's temporary data file path
        :param itemmeta: item metadata dict
        """
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._add_item_internally_locked, (item, revmeta, revdata, revdata_target, itemmeta))

    def _commit_item(self, rev):
        item = rev.item
        metadata = dict(rev)
        md = pickle.dumps(metadata, protocol=PICKLEPROTOCOL)

        rev._fs_file_meta.write(md)

        self._close_revision_meta(rev)
        self._close_revision_data(rev)

        data_hash = metadata[HASH_ALGORITHM]

        pd = self._make_path('data', data_hash)
        if item._fs_item_id is None:
            self._add_item_internally(item, revmeta=rev._fs_path_meta, revdata=rev._fs_path_data, revdata_target=pd)
        else:
            try:
                filesys.rename_no_overwrite(rev._fs_path_data, pd, delete_old=True)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

            pm = self._make_path('meta', item._fs_item_id, '%d.rev' % rev.revno)
            try:
                filesys.rename_no_overwrite(rev._fs_path_meta, pm, delete_old=True)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                raise RevisionAlreadyExistsError("")

    def _rollback_item(self, rev):
        self._close_revision_meta(rev)
        self._close_revision_data(rev)
        os.unlink(rev._fs_path_meta)
        os.unlink(rev._fs_path_data)

    def _destroy_item_locked(self, item):
        item_id = item._fs_item_id

        name2id = self._name2id
        results = name2id.delete().where(name2id.c.item_id==item_id).execute()
        results.close()

        path = self._make_path('meta', item_id)
        try:
            shutil.rmtree(path)
        except OSError as err:
            raise CouldNotDestroyError("Could not destroy item '%r' [errno: %d]" % (
                item.name, err.errno))
        # XXX do refcount data files and if zero, kill it

    def _destroy_item(self, item):
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._destroy_item_locked, item)

    def _change_item_metadata(self, item):
        if not item._fs_item_id is None:
            lp = self._make_path('meta', item._fs_item_id, 'item.lock')
            item._fs_metadata_lock = ExclusiveLock(lp, 30)
            item._fs_metadata_lock.acquire(30)

    def _publish_item_metadata(self, item):
        if item._fs_item_id is None:
            self._add_item_internally(item, itemmeta=item._fs_metadata)
        else:
            assert item._fs_metadata_lock.isLocked()
            md = item._fs_metadata
            if md is None:
                # metadata unchanged
                pass
            elif not md:
                # metadata now empty, just rm the metadata file
                try:
                    os.unlink(self._make_path('meta', item._fs_item_id, 'item'))
                except OSError as err:
                    if err.errno != errno.ENOENT:
                        raise
                    # ignore, there might not have been metadata
            else:
                tmp = self._make_path('meta', item._fs_item_id, 'item.tmp')
                with open(tmp, 'wb') as f:
                    pickle.dump(md, f, protocol=PICKLEPROTOCOL)

                filesys.rename(tmp, self._make_path('meta', item._fs_item_id, 'item'))
            item._fs_metadata_lock.release()
            del item._fs_metadata_lock

    def _get_item_metadata(self, item):
        if item._fs_item_id is not None:
            p = self._make_path('meta', item._fs_item_id, 'item')
            try:
                with open(p, 'rb') as f:
                    metadata = pickle.load(f)
            except IOError as err:
                if err.errno != errno.ENOENT:
                    raise
                # no such file means no metadata was stored
                metadata = {}
            item._fs_metadata = metadata
        return item._fs_metadata

    def _get_revision_metadata(self, rev):
        return rev._fs_metadata

    def _open_revision_data(self, rev, mode='rb'):
        if rev._fs_file_data is None:
            rev._fs_file_data = open(rev._fs_path_data, mode) # XXX keeps file open as long as rev exists

    def _close_revision_data(self, rev):
        if rev._fs_file_data is not None:
            rev._fs_file_data.close()

    def _close_revision_meta(self, rev):
        if rev._fs_file_meta is not None:
            rev._fs_file_meta.close()

    def _seek_revision_data(self, rev, position, mode):
        self._open_revision_data(rev)
        rev._fs_file_data.seek(position, mode)

    def _tell_revision_data(self, rev):
        self._open_revision_data(rev)
        return rev._fs_file_data.tell()

    def _read_revision_data(self, rev, chunksize):
        self._open_revision_data(rev)
        return rev._fs_file_data.read(chunksize)

    def _write_revision_data(self, rev, data):
        # we assume that the file is already open for writing
        rev._fs_file_data.write(data)


