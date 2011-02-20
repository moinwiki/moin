# -*- coding: ascii -*-
"""
    MoinMoin - external static file serving

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from flask import Response, abort
from flask import send_from_directory

from flask import current_app as app

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.apps.serve import serve


@serve.route('/')
def index():
    # show what we have (but not where in the filesystem)
    content = "\n".join(app.cfg.serve_files.keys())
    return Response(content, content_type='text/plain')


@serve.route('/<name>/', defaults=dict(filename=''))
@serve.route('/<name>/<path:filename>')
def files(name, filename):
    try:
        base_path = app.cfg.serve_files[name]
    except KeyError:
        abort(404)

    if not filename:
        abort(404)

    return send_from_directory(base_path, filename)

