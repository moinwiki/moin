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
