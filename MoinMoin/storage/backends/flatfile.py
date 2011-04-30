# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2009-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - flat file backend

    This backend is not useful for a wiki that you actually keep online.
    Instead, it is intended to be used for MoinMoin internally to keep
    the documentation that is part of the source tree editable via the
    wiki server locally.

    This backend stores no item metadata and no old revisions, as such
    you cannot use it safely for a wiki. Inside the MoinMoin source tree,
    however, the wiki content is additionally kept under source control,
    therefore this backend is actually useful to edit documentation that
    is part of MoinMoin.

    The backend _does_ store some revision metadata, namely that which
    used to traditionally be part of the page header.
"""


import os, re, errno
from cStringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError
from MoinMoin.storage.backends._fsutils import quoteWikinameFS, unquoteWikiname
from MoinMoin.storage.backends._flatutils import add_metadata_to_body, split_body
from MoinMoin.config import MIMETYPE, ACTION, MTIME


class FlatFileBackend(Backend):
    def __init__(self, path):
        """
        Initialise filesystem backend, creating initial files and some internal structures.

        :param path: storage path
        """
        self._path = path
        try:
            os.makedirs(path)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise BackendError(str(err))

    def _quote(self, name):
        return quoteWikinameFS(name)

    def _unquote(self, name):
        return unquoteWikiname(name)

    def _rev_path(self, name):
        return os.path.join(self._path, self._quote(name))

    def _exists(self, name):
        revpath = self._rev_path(name)
        return os.path.exists(revpath)

    def history(self, reverse=True):
        rev_list = [i.get_revision(-1) for i in self.iteritems()]
        rev_list.sort(lambda x, y: cmp(x.timestamp, y.timestamp))
        if reverse:
            rev_list.reverse()
        return iter(rev_list)

    def get_item(self, itemname):
        if not self._exists(itemname):
            raise NoSuchItemError("No such item, %r" % (itemname))
        return Item(self, itemname)

    def has_item(self, itemname):
        return self._exists(itemname)

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(itemname)))
        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An Item with the name %r already exists!" % (itemname))
        return Item(self, itemname)

    def iter_items_noindex(self):
        filenames = os.listdir(self._path)
        for filename in filenames:
            yield Item(self, self._unquote(filename))

    iteritems = iter_items_noindex

    def _get_revision(self, item, revno):
        if revno > 0:
            raise NoSuchRevisionError("No Revision #%d on Item %s" % (revno, item.name))

        revpath = self._rev_path(item.name)
        if not os.path.exists(revpath):
            raise NoSuchRevisionError("No Revision #%d on Item %s" % (revno, item.name))

        rev = StoredRevision(item, 0)
        data = open(revpath, 'rb').read()
        rev._metadata, data = split_body(data)
        rev._metadata[ACTION] = 'SAVE'
        rev._metadata[SIZE] = len(data)
        rev._data = StringIO(data)
        return rev

    def _list_revisions(self, item):
        if self._exists(item.name):
            return [0]
        else:
            return []

    def _create_revision(self, item, revno):
        assert revno <= 1
        rev = NewRevision(item, 0)
        rev._data = StringIO()
        return rev

    def _destroy_revision(self, revision):
        revpath = self._rev_path(revision.item.name)
        try:
            os.unlink(revpath)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy revision #%d of item '%r' [errno: %d]" % (
                    revision.revno, revision.item.name, err.errno))
            #else:
            #    someone else already killed this revision, we silently ignore this error

    def _rename_item(self, item, newname):
        try:
            os.rename(self._rev_path(item.name), self._rev_path(newname))
        except OSError:
            raise ItemAlreadyExistsError('')

    def _commit_item(self, rev):
        revpath = self._rev_path(rev.item.name)
        f = open(revpath, 'wb')
        rev._data.seek(0)
        data = rev._data.read()
        data = add_metadata_to_body(rev, data)
        f.write(data)
        f.close()

    def _destroy_item(self, item):
        revpath = self._rev_path(item.name)
        try:
            os.unlink(revpath)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy item '%r' [errno: %d]" % (
                    item.name, err.errno))
            #else:
            #    someone else already killed this item, we silently ignore this error

    def _rollback_item(self, rev):
        pass

    def _change_item_metadata(self, item):
        pass

    def _publish_item_metadata(self, item):
        pass

    def _read_revision_data(self, rev, chunksize):
        return rev._data.read(chunksize)

    def _write_revision_data(self, rev, data):
        rev._data.write(data)

    def _get_item_metadata(self, item):
        return {}

    def _seek_revision_data(self, rev, position, mode):
        rev._data.seek(position, mode)

