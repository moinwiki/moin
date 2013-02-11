# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: the individual patches have same license as the code they are patching

"""
This module contains some monkeypatching for 3rd party code we use.

We hope that any 3rd party might find this code useful and will adopt it,
so we don't need to patch it any more. If you adopt some code from here,
please notify us, so we can remove it from here.
"""


# werkzeug patching ----------------------------------------------------------

# make werkzeug's BaseRequestHandler use some more sane logging format, get
# rid of the duplicate log_date_time_string() werkzeug usually outputs:
import werkzeug.serving
from werkzeug._internal import _log


class BaseRequestHandler(werkzeug.serving.BaseRequestHandler):
    def log(self, type, message, *args):
        _log(type, "{0} {1}\n".format(self.address_string(),
                                message % args))

werkzeug.serving.BaseRequestHandler = BaseRequestHandler
werkzeug.serving.WSGIRequestHandler = BaseRequestHandler
