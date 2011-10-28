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
    ]

    def run(self, filename=None):
        if filename is None:
            f = sys.stdout
        else:
            f = open(filename, "wb")
        with f as f:
            serialize(app.storage.backend, f)


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

