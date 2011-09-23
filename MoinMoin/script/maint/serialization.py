# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - backend serialization / deserialization
"""


from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.storage.middleware.serialization import serialize, deserialize

from MoinMoin import log
logging = log.getLogger(__name__)


class Serialize(Command):
    description = 'Serialize the backend into a file.'

    option_list = [
    ]

    def run(self, filename="dump"):
        serialize(app.storage.backend, open(filename, "wb"))


class Deserialize(Command):
    description = 'Deserialize a file into the backend.'

    option_list = [
    ]

    def run(self, filename="dump"):
        deserialize(open(filename, "rb"), app.storage.backend)

