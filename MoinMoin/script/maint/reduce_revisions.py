# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Reduce Revisions of a backend

This script removes all revisions but the last one from all selected items.
"""


from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin.config import NAME, NAME_EXACT


class Reduce_Revisions(Command):
    description = "This command can be used to remove all revisions but the last one from all selected items."
    option_list = (
        Option('--query', '-q', dest="query", type=unicode, default='',
               help='Only perform the operation on items found by the given query.'),
    )

    def run(self, query):
        storage = app.unprotected_storage
        if query:
            qp = storage.query_parser([NAME_EXACT, ])
            q = qp.parse(query)
        else:
            q = Every()
        results = storage.search(q, limit=None)
        for result in results:
            item_name = result[NAME]
            item = storage.get_item(item_name)
            current_revno = item.next_revno - 1
            for revno in item.list_revisions():
                if revno < current_revno:
                    rev = item.get_revision(revno)
                    print "Destroying {0!r} revision {1}.".format(item_name, revno)
                    rev.destroy()

        print "Finished reducing backend."

