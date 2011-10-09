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

from MoinMoin.config import MTIME, SIZE, CONTENTTYPE
from . import BackendBase

from MoinMoin.util.mimetype import MimeType


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
        # XXX unsafe keys?
        return os.path.join(self.path, key)

    def _mkkey(self, path):
        root = self.path
        assert path.startswith(root)
        key = path[len(root)+1:]
        return key

    def __iter__(self):
        # note: instead of just yielding the relative <path>, yield <path>/<mtime>,
        # so if the file is updated, the revid will change (and the indexer's
        # update() method can efficiently update the index).
        for dirpath, dirnames, filenames in os.walk(self.path):
            key = self._mkkey(dirpath)
            if key:
                yield key
            for filename in filenames:
                yield self._mkkey(os.path.join(dirpath, filename))

    def _get_meta(self, fn):
        path = self._mkpath(fn)
        try:
            st = os.stat(path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise KeyError(fn)
            raise
        meta = {}
        meta[MTIME] = int(st.st_mtime) # use int, not float
        if stat.S_ISDIR(st.st_mode):
            # directory
            # we create a virtual wiki page listing links to subitems:
            ct = 'text/x.moin.wiki;charset=utf-8'
            size = 0
        elif stat.S_ISREG(st.st_mode):
            # normal file
            ct = MimeType(filename=fn).content_type()
            size = int(st.st_size) # use int instead of long
        else:
            # symlink, device file, etc.
            ct = 'application/octet-stream'
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
            content.extend(u" * [[/%s|%s/]]" % (name, name) for name in sorted(dirs))
            content.extend(u" * [[/%s|%s]]" % (name, name) for name in sorted(files))
            content.append(u"")
            content = u'\r\n'.join(content)
        except OSError as err:
            content = unicode(err)
        return content

    def _get_data(self, fn):
        path = self._mkpath(fn)
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
                raise KeyError(fn)
            raise

    def retrieve(self, fn):
        meta = self._get_meta(fn)
        data = self._get_data(fn)
        return meta, data

