# Copyright: 2008 MoinMoin:PawelPacana
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MercurialBackend

    This package contains code for MoinMoin storage backend using a
    Mercurial (hg) distributed version control system. This backend provides
    several advantages compared to MoinMoin's default filesystem backend:
    - revisioning and concurrency issues handled using Mercurial's internal
      mechanisms
    - cloning of the page database, allowing easy backup, synchronization and
      forking of wikis
    - offline, commandline edits with support of custom mercurial extensions
      for non-trivial tasks

    Note: the related MoinMoin/action/GraphInfo.py code, which provided a
          graphical history view for hg backend was removed at 2010-09-25,
          because it needed refactoring for flask/jinja2, but was unmaintained.
          If you'ld like to work on it, pull it from repo history.
"""

from __future__ import with_statement

import os
import time
import errno
import weakref
import tempfile
import StringIO
import itertools
import cPickle as pickle
from datetime import datetime
import hashlib

os.environ["HGENCODING"] = "utf-8" # must be set before importing mercurial
os.environ["HGMERGE"] = "internal:fail"

from mercurial import hg, ui, util, cmdutil, commands
from mercurial.node import short, nullid
from mercurial.revlog import LookupError

try:
    from mercurial.error import RepoError
except ImportError:
    from mercurial.repo import RepoError

try:
    import mercurial.match
except ImportError:
    pass

try:
    import cdb
except ImportError:
    from MoinMoin.util import pycdb as cdb

from MoinMoin.items import USERID, COMMENT
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import (BackendError, NoSuchItemError, NoSuchRevisionError,
                                   RevisionNumberMismatchError, ItemAlreadyExistsError,
                                   RevisionAlreadyExistsError)
WINDOW_SIZE = 256
PICKLE_PROTOCOL = 1
DEFAULT_USER = 'storage'
DEFAULT_COMMIT_MESSAGE = '...'
WIKI_METADATA_PREFIX = '_meta_'
BACKEND_METADATA_PREFIX = '_backend_'

class MercurialBackend(Backend):
    """Implements backend storage using Mercurial VCS."""

    def __init__(self, path):
        """
        Create data directories and initialize mercurial repository.
        If direcrories or repository exists, reuse it. Create name-mapping.
        """
        self._path = os.path.abspath(path)
        self._rev_path = os.path.join(self._path, 'rev')
        self._meta_path = os.path.join(self._path, 'meta')
        self._meta_db = os.path.join(self._meta_path, 'name-mapping')
        try:
            self._ui = ui.ui(quiet=True, interactive=False)
        except:
            self._ui = ui.ui()
            self._ui.setconfig('ui', 'quiet', 'true')
            self._ui.setconfig('ui', 'interactive', 'false')
        for path in (self._path, self._rev_path, self._meta_path):
            try:
                os.makedirs(path)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise BackendError(str(err))
        try:
            self._repo = hg.repository(self._ui, self._rev_path)
        except RepoError:
            self._repo = hg.repository(self._ui, self._rev_path, create=True)

        self._rev_item_lockrefs = {}    # versioned items lock references
        self._meta_item_lockrefs = {}   # non-versioned items lock references
        self._create_cdb()

    def get_item(self, itemname):
        """
        Return an Item with given name.
        Raise NoSuchItemError if Item does not exist.
        """
        id = self._hash(itemname)
        try:
            self._repo.changectx('')[id]
        except LookupError:
            if not self._has_meta(id):
                raise NoSuchItemError('Item does not exist: %s' % itemname)
        item = Item(self, itemname)
        item._id = id
        return item

    def has_item(self, itemname):
        """Return True if Item with given name exists."""
        id = self._hash(itemname)
        return id in self._repo.changectx('') or self._has_meta(id)

    def create_item(self, itemname):
        """
        Create Item with given name.
        Raise ItemAlreadyExistsError if Item already exists.
        Return Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % type(itemname))
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        item = Item(self, itemname)
        item._id = None
        return item

    def iteritems(self):
        """
        Return generator for iterating through collection of Items
        in repository.
        """
        def filter(id):
            return id.endswith(".rev") or id.endswith(".rip")

        ctx = self._repo.changectx('')
        for id in itertools.ifilterfalse(filter, ctx):
            item = Item(self, self._name(id))
            item._id = id
            yield item
        c = cdb.init(self._meta_db)
        record = c.each()
        while record:
            item = Item(self, record[1])
            item._id = record[0]
            yield item
            record = c.each()

    def history(self, reverse=True):
        """
        Return generator for iterating in given direction over Item Revisions
        with timestamp order preserved.
        Yields MercurialStoredRevision objects.
        """
        def restore_revision(name, id):
            item = Item(self, name)
            item._id = id
            rev = MercurialStoredRevision(item, revno, timestamp)
            rev._item_id = item._id
            return rev

        # this is costly operation, but no better idea now how to do it and not
        # break pull/merge stuff
        renamed_items = {}
        for ctx in self._iter_changelog(filter_meta='renamed_to'):
            meta = self._decode_metadata(ctx.extra(), BACKEND_METADATA_PREFIX)
            oldid, renamed_to = meta['renamed_id'], meta['renamed_to']
            renamed_items.setdefault(oldid, []).append(renamed_to)

        for ctx in self._iter_changelog(reverse=reverse):
            meta = self._decode_metadata(ctx.extra(), BACKEND_METADATA_PREFIX)
            revno, oldid, oldname, timestamp = meta['rev'], meta['id'], meta['name'], long(ctx.date()[0])
            try:
                for (id, name) in renamed_items[oldid]:
                    # consider you have backend merged from two instances,
                    # where there was item A renamed to B in first, and the same A
                    # renamed to C in second
                    yield restore_revision(name, id)
            except KeyError:
                yield restore_revision(oldname, oldid)

    def _get_revision(self, item, revno):
        """
        Return given Revision of an Item. Raise NoSuchRevisionError
        if Revision does not exist.
        Return MercurialStoredRevision object.
        """
        try:
            with self._revisions_index(item) as index:
                if revno == -1:
                    revno = index.last_key
                if revno not in index:
                    raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)
        except IOError:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)

        revision = MercurialStoredRevision(item, revno)
        revision._item_id = item._id
        revision._metadata = None
        revision._data = None
        return revision

    def _list_revisions(self, item):
        """Return a list of Item Revision numbers."""
        if not item._id:
            return []
        else:
            try:
                with self._revisions_index(item) as index:
                    revs = [key for key in index]
                return revs
            except IOError:
                return []

    def _create_revision(self, item, revno):
        """Create new Item Revision. Return NewRevision object."""
        try:
            with self._revisions_index(item) as index:
                if revno in index:
                    raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
                if revno != index.last_key + 1:
                    raise RevisionNumberMismatchError("Unable to create revision number %d. "
                        "New Revision number must be next to latest Revision number." % revno)
        except IOError:
            if revno != 0:
                raise RevisionNumberMismatchError("Unable to create revision number %d. "
                        "New Revision number must be next to latest Revision number." % revno)

        rev = NewRevision(item, revno)
        rev._data = None
        rev._revno = revno
        rev._item_id = item._id
        rev._tmp_fpath = tempfile.mkstemp("-rev", "tmp-", dir=self._rev_path)[1]
        return rev

    def _destroy_revision(self, revision):
        item = revision.item
        lock = self._lock_rev_item(item)
        try:
            with self._revisions_index(item) as revisions:
                with self._destroyed_index(item, create=True) as destroyed:
                    destroyed[revision.revno] = revisions[revision.revno]
                    del revisions[revision.revno]
                    if destroyed.empty:
                        self._repo[None].add(["%s.rip" % item._id])
            self._commit_files(["%s.rev" % item._id, "%s.rip" % item._id], message='(revision destroy)')
        finally:
            lock.release()

    def _rename_item(self, item, newname):
        """
        Rename given Item name to newname.
        Raise ItemAlreadyExistsError if destination exists.

        Also rename versioned index file to follow new item name.
        """
        newid = self._hash(newname)
        try:
            lock = self._lock_rev_item(item)
            try:
                if self.has_item(newname):
                    raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
                self._repo.changectx('')[item._id]

                src, dst = os.path.join(self._rev_path, item._id), os.path.join(self._rev_path, newid)
                commands.rename(self._ui, self._repo, src, dst)
                commands.rename(self._ui, self._repo, "%s.rev" % src, "%s.rev" % dst)
                # this commit will update items filelog in repository
                # we provide 'name' metadata to be able to use self._name from this internal revision too
                meta = self._encode_metadata({'name': newname,
                                              'renamed_to': (newid, newname),
                                              'renamed_id': item._id}, BACKEND_METADATA_PREFIX)
                self._commit_files(['%s.rev' % item._id, '%s.rev' % newid, item._id, newid], extra=meta,
                        message='(renamed %s to %s)' % (item.name.encode('utf-8'), newname.encode('utf-8')))
            finally:
                lock.release()
        except LookupError:
            pass
        if self._has_meta(item._id):
            lock = self._lock_meta_item(item)
            try:
                src = os.path.join(self._meta_path, "%s.meta" % item._id)
                dst = os.path.join(self._meta_path, "%s.meta" % newid)
                try:
                    util.rename(src, dst)
                except OSError, err:
                    if err == errno.EEXIST:
                        pass  # if metadata is empty, there is no file, only entry in cdb
                self._add_to_cdb(newid, newname, replace=item._id)
            finally:
                lock.release()
        item._id = newid

    def _commit_item(self, revision, second_parent=None):
        """
        Commit given Item Revision to repository. Update and commit Item index file.
        If Revision already exists, raise RevisionAlreadyExistsError.
        """
        # If there hasn't been a timestamp already assigned, assign one.
        # Note: this is done here primarily to avoid test breakage, the production
        #       timestamps are generated by indexing, see update_index()
        if not revision.timestamp:
            revision.timestamp = long(time.time())
        item = revision.item
        lock = self._lock_rev_item(item)
        try:
            if not item._id:
                self._add_item(item)
            elif revision.revno in self._list_revisions(item):
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revision.revno)

            util.rename(revision._tmp_fpath, os.path.join(self._rev_path, item._id))
            if revision.revno > 0:
                parents = [self._get_changectx(self._get_revision(item, revision.revno - 1)).node()]
                if second_parent:
                    parents.append(second_parent)
            else:
                self._revisions_index(item, create=True).close()
                self._repo[None].add([item._id, "%s.rev" % item._id])
                parents = []
            internal_meta = {'rev': revision.revno,
                             'name': item.name,
                             'id': item._id,
                             'parents': " ".join(parents)}
            meta = self._encode_metadata(internal_meta, BACKEND_METADATA_PREFIX)
            meta.update(self._encode_metadata(revision, WIKI_METADATA_PREFIX))

            date = datetime.fromtimestamp(revision.timestamp).isoformat(sep=' ')
            user = revision.get(USERID, DEFAULT_USER).encode("utf-8")
            msg = revision.get(COMMENT, DEFAULT_COMMIT_MESSAGE).encode("utf-8")

            self._commit_files([item._id], message=msg, user=user, extra=meta, date=date)
            self._append_revision(item, revision)
        finally:
            lock.release()

    def _rollback_item(self, revision):
        pass

    def _destroy_item(self, item):
        self._repo[None].remove(['%s.rev' % item._id, item._id], unlink=True)
        with self._destroyed_index(item, create=True) as index:
            if index.empty:
                self._repo[None].add(["%s.rip" % item._id])
            index.truncate()
        self._commit_files(['%s.rev' % item._id, '%s.rip' % item._id, item._id], message='(item destroy)')
        try:
            os.remove(os.path.join(self._meta_path, "%s.meta" % item._id))
        except OSError, err:
            if err.errno == errno.EACCES:
                raise CouldNotDestroyError

    def _change_item_metadata(self, item):
        """Start Item Metadata transaction."""
        if item._id:
            item._lock = self._lock_meta_item(item)

    def _publish_item_metadata(self, item):
        """Dump Item Metadata to file and finish transaction."""
        def write_meta_item(meta_path, metadata):
            fd, fpath = tempfile.mkstemp("-meta", "tmp-", self._meta_path)
            with os.fdopen(fd, 'wb') as f:
                pickle.dump(metadata, f, protocol=PICKLE_PROTOCOL)
            util.rename(fpath, meta_path)

        if item._id:
            if item._metadata is None:
                pass
            elif not item._metadata:
                try:
                    os.remove(os.path.join(self._meta_path, "%s.meta" % item._id))
                except OSError:
                    pass
            else:
                write_meta_item(os.path.join(self._meta_path, "%s.meta" % item._id), item._metadata)
            item._lock.release()
        else:
            self._add_item(item)
            self._add_to_cdb(item._id, item.name)
            if item._metadata:
                write_meta_item(os.path.join(self._meta_path, "%s.meta" % item._id), item._metadata)

    def _open_revision_data(self, revision):
        if revision._data is None:
            revision._data = StringIO.StringIO(self._get_filectx(revision).data())
            # More effective would be to read revision data from working copy if this is last revision,
            # however this involves locking file: there may be read on write operation (_write_revision_data).
            #
            # if revision.revno == self._list_revisions(revision.item)[-1]:
            #   revision._data = open(os.path.join(self._rev_path, revision._item_id))

    def _read_revision_data(self, revision, chunksize):
        """
        Read given amount of bytes of Revision data.
        By default, all data is read.
        """
        self._open_revision_data(revision)
        return revision._data.read(chunksize)

    def _write_revision_data(self, revision, data):
        """Write data to the given Revision."""
        # We can open file in create_revision and pass it here but this would lead
        # to problems as in FSBackend with too many opened files.
        with open(revision._tmp_fpath, 'a') as f:
            f.write(data)

    def _get_item_metadata(self, item):
        """Load Item Metadata from file. Return metadata dictionary."""
        if item._id:
            try:
                with open(os.path.join(self._meta_path, "%s.meta" % item._id), "rb") as f:
                    item._metadata = pickle.load(f)
            except IOError:
                item._metadata = {}
        else:
            item._metadata = {}
        return item._metadata

    def _get_revision_metadata(self, revision):
        """Return given Revision Metadata dictionary."""
        extra = self._get_changectx(revision).extra()
        return self._decode_metadata(extra, WIKI_METADATA_PREFIX)

    def _get_revision_timestamp(self, revision):
        """Return given Revision timestamp"""
        return long(self._get_filectx(revision).date()[0])

    def _get_revision_size(self, revision):
        """Return size of given Revision in bytes."""
        return self._get_filectx(revision).size()

    def _seek_revision_data(self, revision, position, mode):
        """Set the Revisions cursor on the Revisions data."""
        self._open_revision_data(revision)
        revision._data.seek(position, mode)

    def _tell_revision_data(self, revision):
        """Tell the Revision data cursor position."""
        self._open_revision_data(revision)
        return revision._data.tell()

    def _hash(self, itemname):
        """Compute Item ID from given name."""
        return hashlib.new('md5', itemname.encode('utf-8')).hexdigest()

    def _name(self, itemid):
        """Resolve Item name by given ID."""
        try:
            # there is accurate link between fctx and ctx only if there was some change
            # so therefore we take first filelog entry
            fctx = self._repo.changectx('')[itemid].filectx(0)
            meta = fctx.changectx().extra()
            return self._decode_metadata(meta, BACKEND_METADATA_PREFIX)['name']
        except LookupError:
            c = cdb.init(self._meta_db)
            return c.get(itemid)

    def _iter_changelog(self, reverse=True, filter_id=None, start_rev=None, filter_meta=None):
        """
        Return generator fo iterating over repository changelog.
        Yields Changecontext object.
        """
        def split_windows(start, end, windowsize=WINDOW_SIZE):
            while start < end:
                yield start, min(windowsize, end-start)
                start += windowsize

        def wanted(changerev):
            ctx = self._repo.changectx(changerev)
            try:
                meta = self._decode_metadata(ctx.extra(), BACKEND_METADATA_PREFIX)
                if filter_meta is None:
                    item_id, item_rev, item_name = meta['id'], meta['rev'], meta['name']
                    try:
                        item = Item(self, item_name)
                        item._id = item_id
                        with self._destroyed_index(item) as destroyed:
                            # item is destroyed when destroyed index exists, but is empty
                            if destroyed.empty or item_rev in destroyed:
                                check = False
                            else:
                                check = not filter_id or item_id == filter_id
                        return check
                    except IOError:
                        return not filter_id or item_id == filter_id
                else:
                    return filter_meta in meta
            except KeyError:
                return False

        start, end = start_rev or -1, 0
        try:
            size = len(self._repo.changelog)
        except TypeError:
            size = self._repo.changelog.count()
        if not size:
            change_revs = []
        else:
            if not reverse:
                start, end = end, start
            change_revs = cmdutil.revrange(self._repo, ['%d:%d' % (start, end, )])

        for i, window in split_windows(0, len(change_revs)):
            revs = [changerev for changerev in change_revs[i:i+window] if wanted(changerev)]
            for revno in revs:
                yield self._repo.changectx(revno)

    def _get_filectx(self, revision):
        """
        Get Filecontext object corresponding to given Revision.
        Retrieve necessary information from index file.
        """
        with self._revisions_index(revision.item) as index:
            data = index[revision.revno]
            fctx = self._repo.filectx(data['id'], fileid=data['filenode'])
        return fctx

    def _get_changectx(self, revision):
        """
        Get Changecontext object corresponding to given Revision.
        Retrieve necessary information from index file.
        """
        with self._revisions_index(revision.item) as index:
            ctx = self._repo.changectx(index[revision.revno]['node'])
        return ctx

    def _lock(self, lockpath, lockref):
        """Acquire weak reference to lock object."""
        if lockref and lockref():
            return lockref()
        lock = self._repo._lock(lockpath, wait=True, releasefn=None, acquirefn=None, desc='')
        lockref = weakref.ref(lock)
        return lock

    def _lock_meta_item(self, item):
        """Acquire Item Metadata lock."""
        return self._lock_item(item, self._meta_path, self._meta_item_lockrefs)

    def _lock_rev_item(self, item):
        """Acquire versioned Item lock."""
        return self._lock_item(item, self._rev_path, self._rev_item_lockrefs)

    def _lock_item(self, item, root_path, lock_dict):
        path = os.path.join(root_path, "%s.lock" % item._id)
        return self._lock(path, lock_dict.setdefault(item._id, None))

    def _add_item(self, item):
        """Assign ID to given Item. Raise ItemAlreadyExistsError if Item exists."""
        if self.has_item(item.name):
            raise ItemAlreadyExistsError("Destination item already exists: %s" % item.name)
        item._id = self._hash(item.name)

    def _append_revision(self, item, revision):
        """Add Item Revision to index file to speed up further lookups."""
        fctx = self._repo.changectx('')[item._id]
        with self._revisions_index(item, create=True) as index:
            index[revision.revno] = {'node': short(fctx.node()), 'id': item._id, 'filenode': short(fctx.filenode())}
        self._commit_files(['%s.rev' % item._id], message='(revision append)')

    def _commit_files(self, files, message=DEFAULT_COMMIT_MESSAGE, user=DEFAULT_USER, extra={}, date=None, force=True):
        try:
            match = mercurial.match.exact(self._rev_path, '', files)
            self._repo.commit(match=match, text=message, user=user, extra=extra, date=date, force=force)
        except NameError:
            self._repo.commit(files=files, text=message, user=user, extra=extra, date=date, force=force)

    def _encode_metadata(self, dict, prefix):
        meta = {}
        for k, v in dict.iteritems():
            meta["%s%s" % (prefix, k)] = pickle.dumps(v)
        return meta

    def _decode_metadata(self, dict, prefix):
        meta = {}
        for k, v in dict.iteritems():
            if k.startswith(prefix):
                meta[k[len(prefix):]] = pickle.loads(v)
        return meta

    def _has_meta(self, itemid):
        """Return True if Item with given ID has Metadata. Otherwise return None."""
        c = cdb.init(self._meta_db)
        return c.get(itemid)

    def _add_to_cdb(self, itemid, itemname, replace=None):
        """Add Item Metadata file to name-mapping."""
        c = cdb.init(self._meta_db)
        maker = cdb.cdbmake("%s.ndb" % self._meta_db, "%s.tmp" % self._meta_db)
        record = c.each()
        while record:
            id, name = record
            if id == itemid:
                maker.finish()
                os.unlink(self._meta_db + '.ndb')
                raise ItemAlreadyExistsError("Destination item already exists: %s" % itemname)
            elif id == replace:
                pass
            else:
                maker.add(id, name)
            record = c.each()
        maker.add(itemid, itemname.encode('utf-8'))
        maker.finish()
        util.rename("%s.ndb" % self._meta_db, self._meta_db)

    def _create_cdb(self):
        """Create name-mapping file for storing Item Metadata files mappings."""
        if not os.path.exists(self._meta_db):
            maker = cdb.cdbmake(self._meta_db, "%s.tmp" % self._meta_db)
            maker.finish()

    def _destroyed_index(self, item, create=False):
        return Index(os.path.join(self._rev_path, "%s.rip" % item._id), create)

    def _revisions_index(self, item, create=False):
        return Index(os.path.join(self._rev_path, "%s.rev" % item._id), create)


    # extended API below - needed for drawing revision graph
    def _get_revision_node(self, revision):
        """
        Return tuple consisting of (SHA1, short SHA1) changeset (node) IDs
        corresponding to given Revision.
        """
        try:
            with self._open_item_index(revision.item) as revfile:
                revs = revfile.read().splitlines()
            node = revs[revision.revno].split()[1]
            return node, short(node)
        except IOError:
            return nullid, short(nullid)

    def _get_revision_parents(self, revision):
        """Return parent revision numbers of Revision."""
        def get_revision(node):
            meta = self._repo.changectx(node).extra()
            return self._decode_metadata(meta, BACKEND_METADATA_PREFIX)['rev']

        meta = self._get_changectx(revision).extra()
        parents = self._decode_metadata(meta, BACKEND_METADATA_PREFIX)['parents'].split()
        return [get_revision(node) for node in parents]


class MercurialStoredRevision(StoredRevision):

    def __init__(self, item, revno, timestamp=None, size=None):
        StoredRevision.__init__(self, item, revno, timestamp, size)
        self._data = None

    def get_parents(self):
        return self._backend._get_revision_parents(self)

    def get_node(self):
        return self._backend._get_revision_node(self)


class Index(object):
    """
    Keys are int, values are dictionaries with keys: 'id', 'node', 'filenode'.
    Fixed record size to ease reverse file lookups. Record consists of (in order):
    revno(6 chars), id(32 chars), node(12 chars), filenode(12 chars) separated by
    whitespace.
    """
    RECORD_SAMPLE = '000001 cdfea0c03df2d58eeb8e509ffeab1c94 abfa65835085 b80de5d13875\n'

    def __init__(self, fpath, create=False):
        if create:
            self._file = open(fpath, 'a+')
        else:
            self._file = open(fpath)
        self._fpath = fpath

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getitem__(self, key):
        for record in self._iter_record():
            if int(record[0]) == key:
                return {'id': record[1], 'node': record[2], 'filenode': record[3]}
        raise KeyError

    def __setitem__(self, key, value):
        record = "%s %s %s %s\n" % (str(key).zfill(6), value['id'], value['node'], value['filenode'])
        self._file.write(record)
        pass

    def __delitem__(self, key):
        tmp_fd, tmp_path = tempfile.mkstemp("-index", "tmp-", os.path.dirname(self._fpath))
        with open(tmp_path, 'w') as tmp:
            for record in self._iter_record(reverse=False):
                if key != int(record[0]):
                    tmp.write(' '.join(record) + os.linesep)
        util.rename(tmp_path, self._fpath)

    def __iter__(self):
        for record in self._iter_record(reverse=False):
            yield int(record[0])

    def __contains__(self, key):
        if self.empty:
            return False
        for record in self._iter_record():
            if int(record[0]) == key:
                return True
        return False

    @property
    def last_key(self):
        try:
            last_record = self._iter_record().next()
            return int(last_record[0])
        except StopIteration:
            return -1

    @property
    def empty(self):
        return os.path.getsize(self._fpath) == 0

    def close(self):
        self._file.close()

    def truncate(self):
        self._file.seek(0)
        self._file.truncate()

    def _iter_record(self, reverse=True):
        """Iterates forwards/backwards on file yielding records."""
        record_size = len(self.RECORD_SAMPLE)
        if reverse:
            self._file.seek(0, 2)
            pointer = self._file.tell()
            pointer -= record_size
            while pointer >= 0:
                self._file.seek(pointer)
                pointer -= record_size
                line = self._file.read(record_size)
                yield line.strip().split()
        else:
            self._file.seek(0)
            for line in self._file:
                yield line.split()


