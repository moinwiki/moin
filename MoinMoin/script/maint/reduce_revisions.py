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
from flask.ext.script import Command, Option

from whoosh.query import Every

from MoinMoin.constants.keys import NAME, NAME_EXACT, REVID


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
            print "Destroying historical revisions of {0!r}:".format(current_name)
            has_historical_revision = False
            for rev in current_rev.item.iter_revs():
                revid = rev.meta[REVID]
                if revid == current_revid:
                    continue
                has_historical_revision = True
                name = rev.meta[NAME]
                if name == current_name:
                    print "    Destroying revision {0}".format(revid)
                else:
                    print "    Destroying revision {0} (named {1!r})".format(revid, name)
                current_rev.item.destroy_revision(revid)
            if not has_historical_revision:
                print "    (no historical revisions)"

        print "Finished reducing backend."
