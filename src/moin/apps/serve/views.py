# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - external static file serving
"""


from flask import Response, abort
from flask import send_from_directory

from flask import current_app as app

from moin.apps.serve import serve

from moin import log

logging = log.getLogger(__name__)


@serve.route("/")
def index():
    # show what we have (but not where in the filesystem)
    content = "\n".join(app.cfg.serve_files.keys())
    return Response(content, content_type="text/plain")


@serve.route("/<name>/", defaults=dict(filename=""))
@serve.route("/<name>/<path:filename>")
def files(name, filename):
    try:
        base_path = app.cfg.serve_files[name]
    except KeyError:
        abort(404)

    if not filename:
        abort(404)

    return send_from_directory(base_path, filename)
