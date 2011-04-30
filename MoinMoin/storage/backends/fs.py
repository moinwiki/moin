# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2009-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - FS (filesystem) backend

    XXX: Does NOT work on win32. some problems are documented below (see XXX),
         some are maybe NOT.
"""


import os, struct, tempfile, random, errno, shutil
import cPickle as pickle

from MoinMoin import log
logging = log.getLogger(__name__)

try:
    import cdb
except ImportError:
    from MoinMoin.util import pycdb as cdb

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


class Item(ItemBase):
    pass

class StoredRevision(StoredRevisionBase):
    pass

class NewRevision(NewRevisionBase):
    pass

class FSBackend(BackendBase):
    """
    Basic filesystem backend, described at
    http://moinmo.in/JohannesBerg/FilesystemStorage
    """
    def __init__(self, path, reserved_metadata_space=508):
        """
        Initialise filesystem backend, creating initial files and
        some internal structures.

        :param path: storage path
        :param reserved_metadata_space: space reserved for revision metadata
                                        initially, increase if you expect a
                                        lot of very long ACL strings or so.
                                        We need four additional bookkeeping bytes
                                        so the default of 508 means data starts
                                        at byte 512 in the file by default.
        """
        self._path = path
        self._name_db = os.path.join(path, 'name-mapping')
        self._itemspace = 128
        self._revmeta_reserved_space = reserved_metadata_space

        try:
            os.makedirs(path)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise BackendError(str(err))

        # if no name-mapping db yet, create an empty one
        # (under lock, re-tests existence too)
        if not os.path.exists(self._name_db):
            self._do_locked(self._name_db + '.lock', self._create_new_cdb, None)

    def _create_new_cdb(self, arg):
        """
        Create new name-mapping if it doesn't exist yet,
        call this under the name-mapping.lock.
        """
        if not os.path.exists(self._name_db):
            maker = cdb.cdbmake(self._name_db, self._name_db + '.tmp')
            maker.finish()

    def _get_item_id(self, itemname):
        """
        Get ID of item (or None if no such item exists)

        :param itemname: name of item (unicode)
        """
        c = cdb.init(self._name_db)
        return c.get(itemname.encode('utf-8'))

    def get_item(self, itemname):
        item_id = self._get_item_id(itemname)
        if item_id is None:
            raise NoSuchItemError("No such item '%r'." % itemname)

        item = Item(self, itemname)
        item._fs_item_id = item_id
        item._fs_metadata = None

        return item

    def has_item(self, itemname):
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must be of str/unicode type, not %s." % type(itemname))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An item '%r' already exists!" % itemname)

        item = Item(self, itemname)
        item._fs_item_id = None
        item._fs_metadata = {}

        return item

    def iter_items_noindex(self):
        c = cdb.init(self._name_db)
        r = c.each()
        while r:
            item = Item(self, r[0].decode('utf-8'))
            item._fs_item_id = r[1]
            yield item
            r = c.each()

    iteritems = iter_items_noindex

    def _get_revision(self, item, revno):
        item_id = item._fs_item_id

        if revno == -1:
            revs = item.list_revisions()
            if not revs:
                raise NoSuchRevisionError("Item has no revisions.")
            revno = max(revs)

        revpath = os.path.join(self._path, item_id, 'rev.%d' % revno)
        if not os.path.exists(revpath):
            raise NoSuchRevisionError("Item '%r' has no revision #%d." % (item.name, revno))

        rev = StoredRevision(item, revno)
        rev._fs_revpath = revpath
        rev._fs_file = None
        rev._fs_metadata = None

        return rev

    def _list_revisions(self, item):
        if item._fs_item_id is None:
            return []
        p = os.path.join(self._path, item._fs_item_id)
        l = os.listdir(p)
        ret = sorted([int(i[4:]) for i in l if i.startswith('rev.')])
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

        rev = NewRevision(item, revno)
        rev._revno = revno
        fd, rev._fs_revpath = tempfile.mkstemp('-rev', 'tmp-', self._path)
        rev._fs_file = f = os.fdopen(fd, 'wb+') # XXX keeps file open as long a rev exists
        f.write(struct.pack('!I', self._revmeta_reserved_space + 4))
        f.seek(self._revmeta_reserved_space + 4)

        return rev

    def _destroy_revision(self, revision):
        if revision._fs_file is not None:
            revision._fs_file.close()
        try:
            os.unlink(revision._fs_revpath)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy revision #%d of item '%r' [errno: %d]" % (
                    revision.revno, revision.item.name, err.errno))
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
        nn = newname.encode('utf-8')
        npath = os.path.join(self._path, item._fs_item_id, 'name')

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                raise ItemAlreadyExistsError("Target item '%r' already exists!" % newname)
            elif v == item._fs_item_id:
                maker.add(nn, v)
            else:
                maker.add(i, v)
            r = c.each()
        maker.finish()

        filesys.rename(self._name_db + '.ndb', self._name_db)
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

    def _rename_item(self, item, newname):
        self._do_locked(os.path.join(self._path, 'name-mapping.lock'),
                        self._rename_item_locked, (item, newname))

    def _add_item_internally_locked(self, arg):
        """
        See _add_item_internally, this is just internal for locked operation.
        """
        item, newrev, metadata = arg
        cntr = 0
        done = False
        while not done:
            itemid = '%d' % random.randint(0, self._itemspace - 1)
            ipath = os.path.join(self._path, itemid)
            cntr += 1
            try:
                os.mkdir(ipath)
                done = True
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
            if cntr > 2 and not done and self._itemspace <= 2 ** 31:
                self._itemspace *= 2
                cntr = 0
            elif cntr > 20:
                # XXX: UnexpectedBackendError() that propagates to user?
                raise Exception('Item space full!')

        nn = item.name.encode('utf-8')

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                # Oops. This item already exists! Clean up and error out.
                maker.finish()
                os.unlink(self._name_db + '.ndb')
                os.rmdir(ipath)
                if newrev is not None:
                    os.unlink(newrev)
                raise ItemAlreadyExistsError("Item '%r' already exists!" % item.name)
            else:
                maker.add(i, v)
            r = c.each()
        maker.add(nn, itemid)
        maker.finish()

        if newrev is not None:
            rp = os.path.join(self._path, itemid, 'rev.0')
            filesys.rename(newrev, rp)

        if metadata:
            # only write metadata file if we have any
            meta = os.path.join(self._path, itemid, 'meta')
            f = open(meta, 'wb')
            pickle.dump(metadata, f, protocol=PICKLEPROTOCOL)
            f.close()

        # write 'name' file of item
        npath = os.path.join(ipath, 'name')
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

        # make item retrievable (by putting the name-mapping in place)
        filesys.rename(self._name_db + '.ndb', self._name_db)

        item._fs_item_id = itemid

    def _add_item_internally(self, item, newrev=None, metadata=None):
        """
        This method adds a new item. It locks the name-mapping database to
        ensure putting the item into place and adding it to the name-mapping
        db is atomic.

        If the newrev or metadata arguments are given, then it also adds the
        revision or metadata to the item before making it discoverable.

        If the item's name already exists, it doesn't do anything but raise
        a ItemAlreadyExistsError; if the newrev was given the file is unlinked.

        :param newrev: new revision's temporary file path
        :param metadata: item metadata dict
        """
        self._do_locked(os.path.join(self._path, 'name-mapping.lock'),
                        self._add_item_internally_locked, (item, newrev, metadata))

    def _commit_item(self, rev):
        item = rev.item
        metadata = dict(rev)
        md = pickle.dumps(metadata, protocol=PICKLEPROTOCOL)

        hasdata = rev._fs_file.tell() > self._revmeta_reserved_space + 4

        if hasdata and len(md) > self._revmeta_reserved_space:
            oldrp = rev._fs_revpath
            oldf = rev._fs_file
            fd, rev._fs_revpath = tempfile.mkstemp('-rev', 'tmp-', self._path)
            rev._fs_file = f = os.fdopen(fd, 'wb+')
            f.write(struct.pack('!I', len(md) + 4))
            # write metadata
            f.write(md)
            # copy already written data
            oldf.seek(self._revmeta_reserved_space + 4)
            shutil.copyfileobj(oldf, f)
            oldf.close()
            os.unlink(oldrp)
        else:
            if not hasdata:
                rev._fs_file.seek(0)
                rev._fs_file.write(struct.pack('!L', len(md) + 4))
            else:
                rev._fs_file.seek(4)
            rev._fs_file.write(md)
        rev._fs_file.close()

        if item._fs_item_id is None:
            self._add_item_internally(item, newrev=rev._fs_revpath)
        else:
            rp = os.path.join(self._path, item._fs_item_id, 'rev.%d' % rev.revno)
            try:
                filesys.rename_no_overwrite(rev._fs_revpath, rp, delete_old=True)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                raise RevisionAlreadyExistsError("")

    def _rollback_item(self, rev):
        rev._fs_file.close()
        os.unlink(rev._fs_revpath)

    def _destroy_item_locked(self, item):
        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if v != item._fs_item_id:
                maker.add(i, v)
            r = c.each()
        maker.finish()

        filesys.rename(self._name_db + '.ndb', self._name_db)
        path = os.path.join(self._path, item._fs_item_id)
        try:
            shutil.rmtree(path)
        except OSError as err:
            raise CouldNotDestroyError("Could not destroy item '%r' [errno: %d]" % (
                item.name, err.errno))

    def _destroy_item(self, item):
        self._do_locked(os.path.join(self._path, 'name-mapping.lock'),
                        self._destroy_item_locked, item)

    def _change_item_metadata(self, item):
        if not item._fs_item_id is None:
            lp = os.path.join(self._path, item._fs_item_id, 'meta.lock')
            item._fs_metadata_lock = ExclusiveLock(lp, 30)
            item._fs_metadata_lock.acquire(30)

    def _publish_item_metadata(self, item):
        if item._fs_item_id is None:
            self._add_item_internally(item, metadata=item._fs_metadata)
        else:
            assert item._fs_metadata_lock.isLocked()
            md = item._fs_metadata
            if md is None:
                # metadata unchanged
                pass
            elif not md:
                # metadata now empty, just rm the metadata file
                try:
                    os.unlink(os.path.join(self._path, item._fs_item_id, 'meta'))
                except OSError as err:
                    if err.errno != errno.ENOENT:
                        raise
                    # ignore, there might not have been metadata
            else:
                tmp = os.path.join(self._path, item._fs_item_id, 'meta.tmp')
                f = open(tmp, 'wb')
                pickle.dump(md, f, protocol=PICKLEPROTOCOL)
                f.close()

                filesys.rename(tmp, os.path.join(self._path, item._fs_item_id, 'meta'))
            item._fs_metadata_lock.release()
            del item._fs_metadata_lock

    def _read_revision_data(self, rev, chunksize):
        if rev._fs_file is None:
            self._get_revision_metadata(rev)
        return rev._fs_file.read(chunksize)

    def _write_revision_data(self, rev, data):
        rev._fs_file.write(data)

    def _get_item_metadata(self, item):
        if item._fs_item_id is not None:
            p = os.path.join(self._path, item._fs_item_id, 'meta')
            try:
                f = open(p, 'rb')
                metadata = pickle.load(f)
                f.close()
            except IOError as err:
                if err.errno != errno.ENOENT:
                    raise
                # no such file means no metadata was stored
                metadata = {}
            item._fs_metadata = metadata
        return item._fs_metadata

    def _get_revision_metadata(self, rev):
        if rev._fs_file is None:
            rev._fs_file = f = open(rev._fs_revpath, 'rb+') # XXX keeps file open as long as rev exists
                                                            # XXX further, this is easily triggered by accessing ANY
                                                            # XXX revision metadata (e.g. the timestamp or size or ACL)
            datastart = f.read(4)
            datastart = struct.unpack('!L', datastart)[0]
            rev._datastart = pos = datastart
        else:
            f = rev._fs_file
            pos = f.tell()
            f.seek(4)
        rev._fs_metadata = pickle.load(f)
        f.seek(pos)
        return rev._fs_metadata

    def _seek_revision_data(self, rev, position, mode):
        if rev._fs_file is None:
            self._get_revision_metadata(rev)

        if mode == 0:
            rev._fs_file.seek(position + rev._datastart, mode)
        else:
            rev._fs_file.seek(position, mode)

    def _tell_revision_data(self, revision):
        if revision._fs_file is None:
            self._get_revision_metadata(revision)

        pos = revision._fs_file.tell()
        return pos - revision._datastart


