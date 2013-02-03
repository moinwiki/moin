# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Set Metadata of a revision

This script duplicates the last revision of the selected item
and sets or removes metadata.
"""


from ast import literal_eval

from flask import current_app as app
from flask.ext.script import Command, Option

from whoosh.query import Every

from MoinMoin.config import NAME, NAME_EXACT
from MoinMoin.script import fatal


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
        if not ((key and value) or (key and remove)) or (key and value and remove):
            fatal("You need to either specify a proper key/value pair or "
                  "only a key you want to delete (with -r set).")

        if not remove:
            try:
                value = literal_eval(value)
            except ValueError:
                fatal("You need to specify a valid Python literal as the argument")

        if query:
            qp = app.storage.query_parser([NAME_EXACT, ])
            q = qp.parse(query_text)
        else:
            q = Every()

        for current_rev in app.storage.search(q, limit=None):
            name = current_rev.meta[NAME]
            newmeta = dict(current_rev.meta)
            if remove:
                newmeta.pop(key)
                print "Processing {0!r}, removing {1}.".format(name, key)
            else:
                newmeta[key] = value
                print "Processing {0!r}, setting {1}={2!r}.".format(name, key, value)
            current_rev.item.store_revision(newmeta, current_rev.data)
