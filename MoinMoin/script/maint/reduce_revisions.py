# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Reduce Revisions of a backend

    This script removes all revisions but the last one from all selected items.
"""


import re
from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin.search import term


class Reduce_Revisions(Command):
    description = "This command can be used to remove all revisions but the last one from all selected items."
    option_list = (
        Option('--pattern', '-p', required=False, dest='pattern', type=unicode, default=".*",
               help="You can limit the operation on certain items whose names match the given pattern."),
    )

    def run(self, pattern):
        storage = app.unprotected_storage
        query = term.NameRE(re.compile(pattern))
        # If no pattern is given, the default regex will match every item.
        for item in storage.search_items(query):
            current_revno = item.next_revno - 1
            for revno in item.list_revisions():
                if revno < current_revno:
                    rev = item.get_revision(revno)
                    rev.destroy()

        print "Finished reducing backend."

