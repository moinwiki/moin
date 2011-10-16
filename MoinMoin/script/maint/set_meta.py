# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Set Metadata of a revision

This script duplicates the last revision of the selected item
and sets or removes metadata.
"""


from ast import literal_eval
from shutil import copyfileobj

from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.config import NAME, NAME_EXACT
from MoinMoin.script import fatal
from MoinMoin.storage.error import NoSuchRevisionError


class Set_Meta(Command):
    description = "This command can be used to set meta data of a new revision."
    option_list = (
        Option('--key', '-k', required=False, dest='key', type=unicode,
               help="The key you want to set/change in the new revision"),
        Option('--value', '-v', dest="value", type=unicode,
               help='The value to set for the given key.'),
        Option('--remove', '-r', dest="remove", action='store_true', default=False,
               help='If you want to delete the key given, add this flag.'),
        Option('--query', '-q', dest="query", type=unicode, default='',
               help='Only perform the operation on items found by the given query.')
    )

    def run(self, key, value, remove, query):
        storage = app.unprotected_storage

        if not ((key and value) or (key and remove)) or (key and value and remove):
            fatal("You need to either specify a proper key/value pair or "
                  "only a key you want to delete (with -r set).")

        if query:
            qp = storage.query_parser([NAME_EXACT, ])
            q = qp.parse(query)
        else:
            q = Every()
        results = storage.search(q, limit=None)
        for result in results:
            item_name = result[NAME]
            item = storage.get_item(item_name)
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
                next_rev[key] = literal_eval(value)
                print "Processing {0!r}, setting {1}={2!r}.".format(item_name, key, value)
            else:
                print "Processing {0!r}, removing {1}.".format(item_name, key)

            item.commit()

