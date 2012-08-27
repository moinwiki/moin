# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2012 MoinMoin:CheerXiao
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Reduce Revisions of a backend

This script removes all revisions but the last one from all selected items.
"""


from flask import current_app as app
from flaskext.script import Command, Option

from whoosh.query import Every

from MoinMoin.config import NAME, NAME_EXACT, REVID


class Reduce_Revisions(Command):
    description = "This command can be used to remove all revisions but the last one from all selected items."
    option_list = (
        Option('--query', '-q', dest="query", type=unicode, default='',
               help='Only perform the operation on items found by the given query.'),
    )

    def run(self, query):
        if query:
            qp = app.storage.query_parser([NAME_EXACT, ])
            q = qp.parse(query_text)
        else:
            q = Every()

        for current_rev in app.storage.search(q, limit=None):
            current_name = current_rev.meta[NAME]
            current_revid = current_rev.meta[REVID]
            for rev in current_rev.item.iter_revs():
                revid = rev.meta[REVID]
                if revid != current_revid:
                    name = rev.meta[NAME]
                    print "Destroying {0!r} revision {1}.".format(name, revid)
                    current_rev.item.destroy_revision(revid)

        print "Finished reducing backend."
