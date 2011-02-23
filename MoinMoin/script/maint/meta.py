# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Set Revision Metadata

    This script can be used to duplicate the last revision of
    every item in the backend and set or change (additional)
    metadata of the new revision.

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from shutil import copyfileobj
from os.path import splitext
from re import compile

from flask import flaskg

from MoinMoin.wsgiapp import init_unprotected_backends
from MoinMoin.script import MoinScript, fatal
from MoinMoin.search import term
from MoinMoin.storage.error import NoSuchRevisionError

class PluginScript(MoinScript):
    """System Page Tagging Script"""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-k", "--key", dest="key", action="store", type='string',
            help="The key you want to set/change in the new revision"
        )
        self.parser.add_option(
            "-v", "--value", dest="value", action="store", type='string',
            help="The system page version you would like to create."
        )
        self.parser.add_option(
            "-r", "--remove", dest="remove", action="store_true", default=False,
            help="If you want to delete the key given, add this flag."
        )
        self.parser.add_option(
            "-p", "--pattern", dest="pattern", action="store", type='string', default=".*",
            help="Only perform the operation on items whose names match the pattern."
        )

    def mainloop(self):
        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        storage = flaskg.unprotected_storage

        key = self.options.key
        val = self.options.value
        remove = self.options.remove
        if not ((key and val) or (key and remove)) or (key and val and remove):
            fatal("You need to either specify a proper key/value pair or " + \
                  "only a key you want to delete (with -r set).")

        pattern = self.options.pattern
        query = term.NameRE(compile(pattern))
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
                # Set or overwrite given metadata key with value
                next_rev[key] = eval(val)
            item.commit()

