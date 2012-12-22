# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - fileserver backend, exposing part of the filesystem (read-only)

Files show as single revision items.

  - metadata is made up from fs metadata + mimetype guessing
  - data is read from the file

Directories create a virtual directory item, listing the files in that
directory.
"""


from __future__ import absolute_import, division

import os
import errno
import stat
from StringIO import StringIO
from werkzeug import url_quote, url_unquote

from MoinMoin.config import NAME, ITEMID, REVID, MTIME, SIZE, CONTENTTYPE, HASH_ALGORITHM
from . import BackendBase

from MoinMoin.util.mimetype import MimeType

NAME_SEP = '/'


class Backend(BackendBase):
    """
    exposes part of the filesystem (read-only)
    """
    @classmethod
    def from_uri(cls, uri):
        return cls(uri)

    def __init__(self, path):
        """
        :param path: base directory (all files/dirs below will be exposed)
        """
        self.path = unicode(path)

    def open(self):
        pass

    def close(self):
        pass

    def _mkpath(self, key):
        """
        key -> itemname, absolute path (strip mtime)
        """
        # XXX unsafe keys?
        try:
            itemname, mtime = key.rsplit('.', 1)
        except ValueError:
            # we only generate revids that look like path.mtime,
            # so if the split does not work, the revid is invalid
            # and we raise KeyError like if the rev is not there
            raise KeyError(key)
        # we get NAME_SEP and need to replace them by os.sep to make valid pathes:
        if os.sep == NAME_SEP:
            relpath = itemname
        else:
            relpath = itemname.replace(NAME_SEP, os.sep)
        return itemname, os.path.join(self.path, relpath)

    def _mkkey(self, path):
        """
        absolute path -> itemname, mtime
        """
        st = os.stat(path)
        root = self.path
        assert path.startswith(root)
        relpath = path[len(root)+1:]
        # we always want to give NAME_SEP-separated names (not backslash):
        if os.sep == NAME_SEP:
            itemname = relpath
        else:
            itemname = relpath.replace(os.sep, NAME_SEP)
        mtime = int(st.st_mtime)
        return itemname, mtime

    def _encode(self, key):
        """
        we need to get rid of slashes in revids because we put them into URLs
        and it would confuse the URL routing.
        """
        return url_quote(key, safe='')

    def _decode(self, qkey):
        return url_unquote(qkey)

    def _get_meta(self, itemname, path):
        try:
            st = os.stat(path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise KeyError(itemname)
            raise
        meta = {}
        meta[NAME] = itemname
        meta[MTIME] = int(st.st_mtime) # use int, not float
        meta[REVID] = unicode(self._encode('%s.%d' % (meta[NAME], meta[MTIME])))
        meta[ITEMID] = meta[REVID]
        meta[HASH_ALGORITHM] = u'' # XXX crap, but sendfile needs it for etag
        if stat.S_ISDIR(st.st_mode):
            # directory
            # we create a virtual wiki page listing links to subitems:
            ct = u'text/x.moin.wiki;charset=utf-8'
            size = 0
        elif stat.S_ISREG(st.st_mode):
            # normal file
            ct = unicode(MimeType(filename=itemname).content_type())
            size = int(st.st_size) # use int instead of long
        else:
            # symlink, device file, etc.
            ct = u'application/octet-stream'
            size = 0
        meta[CONTENTTYPE] = ct
        meta[SIZE] = size
        return meta

    def _make_directory_page(self, path):
        try:
            dirs = []
            files = []
            names = os.listdir(path)
            for name in names:
                filepath = os.path.join(path, name)
                if os.path.isdir(filepath):
                    dirs.append(name)
                else:
                    files.append(name)
            content = [
                u"= Directory contents =",
                u" * [[../]]",
            ]
            content.extend(u" * [[/{0}|{1}/]]".format(name, name) for name in sorted(dirs))
            content.extend(u" * [[/{0}|{1}]]".format(name, name) for name in sorted(files))
            content.append(u"")
            content = u'\r\n'.join(content)
        except OSError as err:
            content = unicode(err)
        return content

    def _get_data(self, itemname, path):
        try:
            st = os.stat(path)
            if stat.S_ISDIR(st.st_mode):
                data = self._make_directory_page(path)
                return StringIO(data.encode('utf-8'))
            elif stat.S_ISREG(st.st_mode):
                return open(path, 'rb')
            else:
                return StringIO('')
        except (OSError, IOError) as e:
            if e.errno == errno.ENOENT:
                raise KeyError(itemname)
            raise

    def __iter__(self):
        # note: instead of just yielding the relative <path>, yield <path>.<mtime>,
        # so if the file is updated, the revid will change (and the indexer's
        # update() method can efficiently update the index).
        for dirpath, dirnames, filenames in os.walk(self.path):
            key, mtime = self._mkkey(dirpath)
            if 1: # key:
                yield self._encode('%s.%d' % (key, mtime))
            for filename in filenames:
                yield self._encode('%s.%d' % self._mkkey(os.path.join(dirpath, filename)))

    def retrieve(self, key):
        key = self._decode(key)
        itemname, path = self._mkpath(key)
        meta = self._get_meta(itemname, path)
        data = self._get_data(itemname, path)
        return meta, data
