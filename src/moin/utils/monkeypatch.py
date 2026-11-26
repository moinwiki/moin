# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2025 MoinMoin Project
# License: The individual patches have the same license as the code they patch.

"""
This module contains some monkey patching for third-party code we use.

We hope that upstream projects find this code useful and adopt it, so we don't
need to patch it anymore. If you adopt some code from here, please notify us so
we can remove it from here.
"""

# werkzeug patching ----------------------------------------------------------

# make werkzeug's WSGIRequestHandler use some more sane logging format, get
# rid of the duplicate log_date_time_string() werkzeug usually outputs:
# 2019-04-10 08:59:20,898 INFO werkzeug:97 127.0.0.1 - - [10/Apr/2019 08:59:20] "GET /Home HTTP/1.1" 200 -
# with this monkeypatch:
# 2019-04-10 09:10:09,273 INFO werkzeug:97 127.0.0.1 "GET /Home HTTP/1.1" 200 -
import werkzeug.serving
from werkzeug._internal import _log


class WSGIRequestHandler(werkzeug.serving.WSGIRequestHandler):
    def log(self, type, message, *args):
        _log(type, f"{self.address_string()} {message % args}\n")


werkzeug.serving.WSGIRequestHandler = WSGIRequestHandler

# Whoosh patching ------------------------------------------------------------

# Reset buffer on close
# See GitHub issues #1645 and #1961

from whoosh.filedb.structfile import BufferFile


def buffer_file_close(self):
    super(BufferFile, self).close()
    self._buf = None


# patch class BufferFile
BufferFile.close = buffer_file_close


# Read from the buffer instead of a copy of it
# whoosh memory-maps the segment files of an index and gives each part of a segment (e.g. its postings or
# its terms) to a BufferFile. BufferFile.__init__ also wraps that part in a BytesIO, which copies all of it
# into memory. moin opens new searchers for every request, so every request copied big parts of the index:
# the postings and terms of every segment, which is most of the index size.


class BufferReader:
    """
    Read-only file object for a buffer (bytes, memoryview, ...), without copying the buffer.

    Supports what whoosh uses of the BytesIO it replaces: read, readline, iteration, seek, tell and close.
    """

    __slots__ = ("_buf", "_pos")

    def __init__(self, buf):
        self._buf = buf
        self._pos = 0

    def _check_open(self):
        if self._buf is None:
            raise ValueError("I/O operation on closed file.")

    def read(self, size=-1):
        self._check_open()
        pos = self._pos
        length = len(self._buf)
        end = length if size is None or size < 0 else min(pos + size, length)
        if end <= pos:
            return b""
        self._pos = end
        return bytes(self._buf[pos:end])

    def readline(self, size=-1):
        self._check_open()
        pos = self._pos
        length = len(self._buf)
        end = length if size is None or size < 0 else min(pos + size, length)
        start = pos
        while start < end:
            # search in chunks, a memoryview has no find()
            chunk_end = min(start + 4096, end)
            newline = bytes(self._buf[start:chunk_end]).find(b"\n")
            if newline >= 0:
                end = start + newline + 1
                break
            start = chunk_end
        if end <= pos:
            return b""
        self._pos = end
        return bytes(self._buf[pos:end])

    def __iter__(self):
        while line := self.readline():
            yield line

    def seek(self, pos, whence=0):
        self._check_open()
        if whence == 0:
            new_pos = pos
        elif whence == 1:
            new_pos = self._pos + pos
        elif whence == 2:
            new_pos = len(self._buf) + pos
        else:
            raise ValueError(f"invalid whence ({whence}, should be 0, 1 or 2)")
        if new_pos < 0:
            raise ValueError(f"negative seek value {new_pos}")
        self._pos = new_pos
        return new_pos

    def tell(self):
        self._check_open()
        return self._pos

    def close(self):
        self._buf = None

    @property
    def closed(self):
        return self._buf is None


def buffer_file_init(self, buf, name=None, onclose=None):
    # same as whoosh's BufferFile.__init__, but self.file does not copy buf
    self._buf = buf
    self._name = name
    self.file = BufferReader(buf)
    self.onclose = onclose
    self.is_real = False
    self.is_closed = False


# patch class BufferFile
BufferFile.__init__ = buffer_file_init

# flask-theme patching -------------------------------------------------------

# Cache the result of searching the file system for theme template files.
# Solves issue <https://github.com/moinwiki/moin/issues/1875>.

import flask_theme

from flask.globals import request_ctx


def template_exists(templatename):
    if (templates := getattr(template_exists, "cache", None)) is None:
        templates = flask_theme.containable(request_ctx.app.jinja_env.list_templates())
        setattr(template_exists, "cache", templates)
    return templatename in templates


flask_theme.template_exists = template_exists

# Fix ThemeManager.refresh() not being safe against concurrent readers.
# The original implementation resets self._themes to an empty dict, then
# repopulates it in place with no lock:
#
#     def refresh(self):
#         self._themes = {}
#         for theme in starchain(...):
#             self.themes[theme.identifier] = theme
#
# A reader on another thread (e.g. another thread of the same freshly
# started/recycled mod_wsgi process, taking its first request around the
# same moment) can observe self._themes as a real, non-None, but still
# empty dict during that window, and raise a spurious KeyError for a
# theme -- including the configured default -- that is about to exist a
# moment later. This is what's behind "KeyError: 'topside'" (or whatever
# theme_default is set to) crashes.
#
# Build the new mapping in a local variable instead, and only publish it
# via a single attribute assignment once it's complete. A single
# attribute assignment is atomic (it's just a pointer write under the
# GIL), so a concurrent reader only ever sees the old, complete mapping
# or the new, complete mapping -- never a partial one. Concurrent callers
# of refresh() may end up redundantly building the same mapping more than
# once, but that's harmless wasted work, not a correctness issue: the
# old mapping is reclaimed by normal reference counting once its last
# reader is done with it, no coordination required.


def theme_manager_refresh(self):
    themes = {}
    for theme in flask_theme.starchain(loader(self.app) for loader in self.loaders):
        if self.valid_app_id(theme.application):
            themes[theme.identifier] = theme
    self._themes = themes


flask_theme.ThemeManager.refresh = theme_manager_refresh
