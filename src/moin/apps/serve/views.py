# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - External static file serving
"""

from __future__ import annotations

from flask import Blueprint, Response, abort, send_from_directory

from moin import current_app, log

logging = log.getLogger(__name__)

serve = Blueprint("serve", __name__)


@serve.route("/")
def index() -> Response:
    # Show what we have (but not where in the filesystem).
    content = "\n".join(current_app.cfg.serve_files.keys())
    return Response(content, content_type="text/plain")


@serve.route("/<name>/", defaults=dict(filename=""))
@serve.route("/<name>/<path:filename>")
def files(name: str, filename: str) -> Response:
    try:
        base_path = current_app.cfg.serve_files[name]
    except KeyError:
        abort(404)

    if not filename:
        abort(404)

    return send_from_directory(base_path, filename)
