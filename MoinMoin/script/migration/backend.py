"""
    MoinMoin - backend migration script

    Migrate 1.7, 1.8 and 1.9 wiki data (including users) to the new
    2.0 storage format.
    Assumptions:
    - defined namespace_mapping in wikiconfig (Contains destination backends.)
    - defined old_instance_path in wikiconfig (may be removed after conversion)

    @copyright: 2008 MoinMoin:PawelPacana,
                2008-2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import shutil, sys
from os.path import join

from flask import flaskg
from flask import current_app as app

from MoinMoin.script import MoinScript, fatal
from MoinMoin.wsgiapp import init_unprotected_backends
from MoinMoin.storage.backends import fs19

class PluginScript(MoinScript):
    """Backend migration class."""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-v", "--verbose", dest="verbose", action="store_true",
            help="Provide progress information while performing the migration"
        )
        self.parser.add_option(
            "-f", "--fails", dest="show_failed", action="store_true",
            help="Print failed migration items"
        )

    def mainloop(self):
        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        cfg = app.cfg

        try:
            data_dir_old = cfg.data_dir_old
            user_dir_old = cfg.user_dir_old
        except AttributeError:
            fatal("""
The backend migration did not find your old wiki data.

Please, configure in your wiki config:
    data_dir_old = '.../data' # must be the path of your old data directory
                              # (it must contain the pages/ subdirectory)
    user_dir_old = '.../data/user' # must be the path of your old user profile directory
                                   # or None (no conversion of user profiles)
""")

        page_backend = fs19.FSPageBackend(data_dir_old)
        dest_content = flaskg.unprotected_storage.get_backend(cfg.ns_content)
        sys.stdout.write("Starting backend migration.\nConverting data.\n")
        content_fails = dest_content.clone(page_backend, self.options.verbose)[2]
        if self.options.show_failed and len(content_fails):
            sys.stdout.write("\nFailed report\n-------------\n")
            for name in content_fails.iterkeys():
                sys.stdout.write("%r: %s\n" % (name, content_fails[name]))
        sys.stdout.write("Content migration finished!\n")

        if user_dir_old:
            user_backend = fs19.FSUserBackend(user_dir_old)
            dest_userprofile = flaskg.unprotected_storage.get_backend(cfg.ns_user_profile)
            sys.stdout.write("Converting users.\n")
            user_fails = dest_userprofile.clone(user_backend, self.options.verbose)[2]
            if self.options.show_failed and len(user_fails):
                sys.stdout.write("\nFailed report\n-------------\n")
                for name in user_fails.iterkeys():
                    sys.stdout.write("%r: %s\n" % (name, user_fails[name]))
            sys.stdout.write("User profile migration finished!\n")

