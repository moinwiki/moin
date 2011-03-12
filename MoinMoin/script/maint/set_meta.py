# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Set Metadata of a revision

    This script duplicates the last revision of the selected item
    and sets or removes metadata.
"""


import re
from ast import literal_eval
from shutil import copyfileobj

from flask import flaskg
from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin.script import fatal
from MoinMoin.search import term
from MoinMoin.storage.error import NoSuchRevisionError

class Set_Meta(Command):
    description = "This command can be used to set meta data of a new revision."
    option_list = (
        Option('--key', '-k', required=False, dest='key', type=unicode,
               help="The key you want to set/change in the new revision"),
        Option('--value', '-v', dest="text", type=unicode,
               help='The value to set for the given key.'),
        Option('--remove', '-r', dest="remove", action='store_true', default=False,
               help='If you want to delete the key given, add this flag.'),
        Option('--pattern', '-p', dest="pattern", type=unicode, default='.*',
               help='Only perform the operation on items whose names match the pattern.')
    )

    def run(self, key, text, remove, pattern):
        storage = app.unprotected_storage

        if not ((key and text) or (key and remove)) or (key and text and remove):
            fatal("You need to either specify a proper key/value pair or "
                  "only a key you want to delete (with -r set).")

        query = term.NameRE(re.compile(pattern))
        for item in storage.search_items(query):
            try:
                last_rev = item.get_revision(-1)
            except NoSuchRevisionError:
                last_rev = None

            next_rev = item.create_revision(item.next_revno)

            if last_rev:
                # Copy data.
                copyfileobj(last_rev, next_rev)
                # Copy metadata:
                for k, v in last_rev.iteritems():
                    if remove and k == key:
                        continue
                    next_rev[k] = v

            if not remove:
                # Set or overwrite given metadata key with text
                value = literal_eval(text)
                next_rev[key] = value
            item.commit()

