"""
    MoinMoin - file server backend

    You can use this backend to directly get read-only access to your
    wiki server's filesystem.

    TODO: nearly working, but needs more work at other places,
          e.g. in the router backend, to be useful.

    @copyright: 2008-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import os, stat
from StringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil, config

from MoinMoin.storage import Backend, Item, StoredRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

from MoinMoin.items import ACL, MIMETYPE, ACTION, COMMENT
MTIME = '__timestamp' # does not exist in storage any more

class FSError(Exception):
    """ file serving backend error """

class NoFileError(FSError):
    """ tried to create a FileItem for a path that is not a file """

class NoDirError(FSError):
    """ tried to create a DirItem for a path that is not a directory """

class FileServerBackend(Backend):
    """
    File Server Backend - serves files directly from host's filesystem

    For method docstrings, please see the "Backend" base class.
    """
    def __init__(self, root_dir):
        """
        Initialise file serving backend.

        @type root_dir: unicode
        @param root_dir: root directory below which we serve files
        """
        root_dir = root_dir.rstrip('/')
        assert root_dir
        self.root_dir = unicode(root_dir)

    def _item2path(self, itemname):
        # XXX check whether ../.. precautions are needed,
        # looks like not, because moin sanitizes the item name before
        # calling the storage code
        return os.path.join(self.root_dir, itemname)

    def _path2item(self, path):
        root = self.root_dir
        assert path.startswith(root)
        return path[len(root)+1:]

    def iteritems(self):
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            yield DirItem(self, self._path2item(dirpath))
            for filename in filenames:
                try:
                    item = FileItem(self, self._path2item(os.path.join(dirpath, filename)))
                except (NoFileError, NoSuchItemError):
                    pass  # not a regular file, maybe socket or ...
                else:
                    yield item

    def get_item(self, itemname):
        try:
            return FileItem(self, itemname)
        except NoFileError:
            try:
                return DirItem(self, itemname)
            except NoDirError:
                raise NoSuchItemError()

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        return item._fs_revisions

    def _get_revision(self, item, revno):
        if isinstance(item, FileItem):
            return FileRevision(item, revno)
        elif isinstance(item, DirItem):
            return DirRevision(item, revno)
        else:
            raise

    def _get_revision_metadata(self, rev):
        return rev._fs_meta

    def _read_revision_data(self, rev, chunksize):
        if rev._fs_data_file is None:
            rev._fs_data_file = open(rev._fs_data_fname, 'rb') # XXX keeps file open as long as rev exists
        return rev._fs_data_file.read(chunksize)

    def _seek_revision_data(self, rev, position, mode):
        if rev._fs_data_file is None:
            rev._fs_data_file = open(rev._fs_data_fname, 'rb') # XXX keeps file open as long as rev exists
        return rev._fs_data_file.seek(position, mode)

    def _get_revision_timestamp(self, rev):
        return rev._fs_meta[MTIME]

    def _get_revision_size(self, rev):
        return rev._fs_meta['__size']


# Specialized Items/Revisions

class FileDirItem(Item):
    """ A filesystem file or directory """
    def __init__(self, backend, name):
        Item.__init__(self, backend, name)
        filepath = backend._item2path(name)
        try:
            self._fs_stat = os.stat(filepath)
        except OSError, err:
            raise NoSuchItemError("No such item, %r" % name)
        self._fs_revisions = [0] # there is only 1 revision of each file/dir
        self._fs_meta = {} # no item level metadata
        self._fs_filepath = filepath

class DirItem(FileDirItem):
    """ A filesystem directory """
    def __init__(self, backend, name):
        FileDirItem.__init__(self, backend, name)
        if not stat.S_ISDIR(self._fs_stat.st_mode):
            raise NoDirError("Item is not a directory: %r" % name)

class FileItem(FileDirItem):
    """ A filesystem file """
    def __init__(self, backend, name):
        FileDirItem.__init__(self, backend, name)
        if not stat.S_ISREG(self._fs_stat.st_mode):
            raise NoFileError("Item is not a regular file: %r" % name)


class FileDirRevision(StoredRevision):
    """ A filesystem file or directory """
    def __init__(self, item, revno):
        if revno > 0:
            raise NoSuchRevisionError('Item %r has no revision %d (filesystem items just have revno 0)!' %
                    (item.name, revno))
        if revno == -1:
            revno = 0
        StoredRevision.__init__(self, item, revno)
        filepath = item._fs_filepath
        st = item._fs_stat
        meta = { # make something up
            MTIME: st.st_mtime,
            ACTION: 'SAVE',
            '__size': st.st_size,
        }
        self._fs_meta = meta
        self._fs_data_fname = filepath
        self._fs_data_file = None

class DirRevision(FileDirRevision):
    """ A filesystem directory """
    def __init__(self, item, revno):
        FileDirRevision.__init__(self, item, revno)
        self._fs_meta.update({
            MIMETYPE: 'text/x.moin.wiki',
        })
        # create a directory "page" in wiki markup:
        try:
            dirs = []
            files = []
            names = os.listdir(self._fs_data_fname)
            for name in names:
                filepath = os.path.join(self._fs_data_fname, name)
                if os.path.isdir(filepath):
                    dirs.append(name)
                else:
                    files.append(name)
            content = [
                u"= Directory contents =",
                u" * [[../]]",
            ]
            content.extend(u" * [[/%s|%s/]]" % (name, name) for name in sorted(dirs))
            content.extend(u" * [[/%s|%s]]" % (name, name) for name in sorted(files))
            content = u'\r\n'.join(content)
        except OSError, err:
            content = unicode(err)
        self._fs_data_file = StringIO(content.encode(config.charset))

class FileRevision(FileDirRevision):
    """ A filesystem file """
    def __init__(self, item, revno):
        FileDirRevision.__init__(self, item, revno)
        mimetype = wikiutil.MimeType(filename=self._fs_data_fname).mime_type()
        self._fs_meta.update({
            MIMETYPE: mimetype,
        })

