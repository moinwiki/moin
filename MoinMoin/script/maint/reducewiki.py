# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Reduce Wiki

    This script can be used to remove all revisions but
    the last ones from all items.
    Handle with great care!

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from re import compile

from flask import flaskg

from MoinMoin.wsgiapp import init_unprotected_backends
from MoinMoin.script import MoinScript, fatal
from MoinMoin.search import term
from MoinMoin.storage.error import NoSuchRevisionError

class PluginScript(MoinScript):
    """Reduce Wiki Script"""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-p", "--pattern", dest="pattern", action="store", type='string', default=".*",
            help="You can limit the operation on certain items whose names match the given pattern."
        )

    def mainloop(self):
        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        storage = flaskg.unprotected_storage

        pattern = self.options.pattern
        query = term.NameRE(compile(pattern))
        # If no pattern is given, the default regex will match every item.
        for item in storage.search_items(query):
            current_revno = item.next_revno - 1
            for revno in item.list_revisions():
                if revno < current_revno:
                    rev = item.get_revision(revno)
                    rev.destroy()

        print "Finished reducing backend."

