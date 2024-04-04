# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: the individual patches have same license as the code they are patching

"""
This module contains some monkeypatching for 3rd party code we use.

We hope that any 3rd party might find this code useful and will adopt it,
so we don't need to patch it any more. If you adopt some code from here,
please notify us, so we can remove it from here.
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
