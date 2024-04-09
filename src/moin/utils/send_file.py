# Copyright: 2010 by Armin Ronacher (initial implementation)
# Copyright: 2011 by MoinMoin:ThomasWaldmann (modifications)
# Copyright: 2023 by MoinMoin project
# License: BSD (see license of flask)

"""
A better send_file
------------------

Initially, this was a modified implementation of flask 0.6.0's send_file(),
trying to be as compatible as possible.

For details see: https://github.com/pallets/flask/issues/104 and the
history of this file in our repository. This code fixes all the issues
described in the bug report.

As we forked send_file, we later modified it (without trying to stay
compatible), because we can easily adapt anyway and the code can be much
simpler without compatibility code.
"""


import os
import mimetypes
from time import time
from zlib import adler32

from urllib.parse import quote
from werkzeug.datastructures import Headers
from werkzeug.wsgi import wrap_file
from flask import current_app, request


def encode_rfc2231(value, coding="UTF-8", lang=""):
    """
    Encode a value according to RFC2231/5987.

    :param value: the value to encode. must be either unicode or encoded in <coding>.
    :param coding: the coding (charset) to use. it is a good idea to use 'UTF-8'.
    :param lang: the language to use. defaults to empty string (no language given).
    """
    return f"{coding}'{lang}'{quote(value, encoding=coding)}"


def send_file(
    filename=None,
    file=None,
    mimetype=None,
    as_attachment=False,
    attachment_filename=None,
    mtime=None,
    cache_timeout=60 * 60 * 12,
    add_etags=True,
    etag=None,
    conditional=False,
):
    """Sends the contents of a file to the client.

    A file can be either a filesystem file or a file-like object (this code
    is careful about not assuming that every file is a filesystem file).

    This will use the most efficient method available, configured and possible
    (for filesystem files some more optimizations may be possible that for
    file-like objects not having a filesystem filename).
    By default it will try to use the WSGI server's file_wrapper support.
    Alternatively you can set ``USE_X_SENDFILE = True`` in the application's
    config to directly emit an `X-Sendfile` header.  This
    however requires support of the underlying webserver for `X-Sendfile`.

    send_file will try to guess some stuff for you if you do not provide them:

    * mimetype (based on filename / attachment_filename)
    * mtime (based on filesystem file's metadata)
    * etag (based on filename, mtime, filesystem file size)

    If you do not provide enough information, send_file might raise a
    TypeError.

    For extra security you probably want to sent certain files as attachment
    (HTML for instance).

    Please never pass filenames to this function from user sources without
    checking them first.  Something like this is usually sufficient to
    avoid security problems::

        if '..' in filename or filename.startswith('/'):
            abort(404)

    :param filename: the filesystem filename of the file to send (relative to
                     the :attr:`~Flask.root_path` if a relative path is
                     specified).
                     If you just have an open filesystem file object f, give
                     `f.name` here.
                     If you don't have a filesystem file nor a filesystem file
                     name, but just a file-like obj, don't use this argument.
    :param file: a file (or file-like) object, you may give it if you either do
                 not have a filesystem filename or if you already have an open
                 file anyway.
    :param mimetype: the mimetype of the file if provided, otherwise
                     auto detection happens based on the filename or
                     attachment_filename.
    :param as_attachment: set to `True` if you want to send this file with
                          a ``Content-Disposition: attachment`` header.
    :param attachment_filename: the filename for the attachment if it
                                differs from the filename argument.
    :param mtime: the modification time of the file if provided, otherwise
                  it will be determined automatically for filesystem files
    :param cache_timeout: the timeout in seconds for the headers.
    :param conditional: set to `True` to enable conditional responses.
    :param add_etags: set to `False` to disable attaching of etags.
    :param etag: you can give an etag here, None means to try to compute the
                 etag from the file's filesystem metadata (the latter of course
                 only works for filesystem files). If you do not give a
                 filename, but you use add_etags, you must explicitely provide
                 the etag as it can't compute it for that case.
    """
    if filename and not os.path.isabs(filename):
        filename = os.path.join(current_app.root_path, filename)

    if mimetype is None and (filename or attachment_filename):
        mimetype = mimetypes.guess_type(filename or attachment_filename)[0]
    if mimetype is None:
        mimetype = "application/octet-stream"

    headers = Headers()

    # We must compute size the smart way rather than letting
    # werkzeug turn our iterable into an in-memory sequence
    # See `_ensure_sequence` in werkzeug/wrappers.py
    if filename:
        fsize = os.path.getsize(filename)
    elif file and hasattr(file, "seek") and hasattr(file, "tell"):
        fsize = None
        # be extra careful as some file-like objects (like zip members) have a seek
        # and tell methods, but they just raise some exception (e.g. UnsupportedOperation)
        # instead of really doing what they are supposed to do (or just be missing).
        try:
            file.seek(0, 2)  # seek to EOF
            try:
                fsize = file.tell()  # tell position
            except Exception:
                pass
            file.seek(0, 0)  # seek to start of file
        except Exception:
            pass
    else:
        fsize = None
    if fsize is not None:
        headers.add("Content-Length", fsize)

    if as_attachment:
        if attachment_filename is None:
            if not filename:
                raise TypeError("filename unavailable, required for sending as attachment")
            attachment_filename = os.path.basename(filename)
        # Note: we only give filename* param, not filename param, hoping that a user agent that
        # does not support filename* then falls back into using the last URL fragment (and decodes
        # that correctly). See there for details: http://greenbytes.de/tech/tc2231/
        headers.add("Content-Disposition", f"attachment; filename*={encode_rfc2231(attachment_filename)}")

    if current_app.config["USE_X_SENDFILE"] and filename:
        if file:
            file.close()
        headers["X-Sendfile"] = filename
        data = None
    else:
        if filename:
            if not file:
                file = open(filename, "rb")
            if mtime is None:
                mtime = os.path.getmtime(filename)
        data = wrap_file(request.environ, file)

    rv = current_app.response_class(data, mimetype=mimetype, headers=headers, direct_passthrough=True)

    # if we know the file modification date, we can store it as the
    # current time to better support conditional requests.  Werkzeug
    # as of 0.6.1 will override this value however in the conditional
    # response with the current time.  This will be fixed in Werkzeug
    # with a new release, however many WSGI servers will still emit
    # a separate date header.
    if mtime is not None:
        rv.date = int(mtime)

    rv.cache_control.public = True
    if cache_timeout:
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time() + cache_timeout)

    if add_etags:
        if etag is None and filename:
            filename_encoded = filename if isinstance(filename, bytes) else filename.encode()
            etag = "flask-{}-{}-{}".format(
                mtime or os.path.getmtime(filename), os.path.getsize(filename), adler32(filename_encoded) & 0xFFFFFFFF
            )
        if etag is None:
            raise TypeError("can't determine etag - please give etag or filename")
        rv.set_etag(etag)
        if conditional:
            rv = rv.make_conditional(request)
            # make sure we don't send x-sendfile for servers that
            # ignore the 304 status code for x-sendfile.
            if rv.status_code == 304:
                rv.headers.pop("x-sendfile", None)
    return rv
