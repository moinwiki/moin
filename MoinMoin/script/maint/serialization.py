# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend serialization / deserialization
"""

import sys

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.storage.middleware.serialization import serialize, deserialize

from MoinMoin import log
logging = log.getLogger(__name__)


class Serialize(Command):
    description = 'Serialize the backend into a file.'

    option_list = [
        Option('--file', '-f', dest='filename', type=unicode, required=False,
               help='Filename of the output file.'),
        Option('--backends', '-b', dest='backends', type=unicode, required=False,
               help='Backend names to serialize (comma separated).'),
        Option('--all-backends', '-a', dest='all_backends', action='store_true', default=False,
               help='Serialize all configured backends.'),
    ]

    def run(self, filename=None, backends=None, all_backends=False):
        if filename is None:
            f = sys.stdout
        else:
            f = open(filename, "wb")
        with f as f:
            existing_backends = set(app.cfg.backend_mapping)
            if all_backends:
                backends = set(app.cfg.backend_mapping)
            elif backends:
                backends = set(backends.split(','))
            if backends:
                # low level - directly serialize some backend contents -
                # this does not use the index:
                if backends.issubset(existing_backends):
                    for backend_name in backends:
                        backend = app.cfg.backend_mapping.get(backend_name)
                        serialize(backend, f)
                else:
                    print "Error: Wrong backend name given."
                    print "Given Backends: %r" % backends
                    print "Configured Backends: %r" % existing_backends


class Deserialize(Command):
    description = 'Deserialize a file into the backend.'

    option_list = [
        Option('--file', '-f', dest='filename', type=unicode, required=False,
               help='Filename of the input file.'),
    ]

    def run(self, filename=None):
        if filename is None:
            f = sys.stdin
        else:
            f = open(filename, "rb")
        with f as f:
            deserialize(f, app.storage.backend)

