# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Extension Script Package
"""

import sys

from flask_script import Manager, Server, Command

import moin


class Help(Command):
    description = 'Quick help'

    def run(self):
        # TODO: add more help here as soon as stuff has been migrated from "m" to "moin".
        print("""\
Quick help / most important commands overview:

moin index-create  # create index (optionally also create empty storage)

moin moin  # run moin's builtin web server

moin import19  # import data from moin 1.9

moin index-build  # (re)build index

For more information please see:

- "moin --help" command output
- "moin <subcommand> --help" command output
- docs
""")


def main(default_command='help', wiki_config=None):
    """
    console_script entry point
    """
    from moin.app import create_app

    manager = Manager(create_app)
    manager.add_option('-c', '--config', dest='config', required=False, default=wiki_config)
    manager.add_option('-i', '--index-create', action='store_true', dest='create_index',
                       required=False, default=False)
    manager.add_option('-s', '--storage-create', action='store_true', dest='create_storage',
                       required=False, default=False)

    manager.add_command("help", Help())
    manager.add_command("moin", Server(host='127.0.0.1', port=8080))
    manager.add_command("run", Server(host='127.0.0.1', port=8080))

    from moin.scripts.maint import create_instance
    manager.add_command("create-instance", create_instance.CreateInstance())

    from moin.scripts.maint import index
    manager.add_command("index-create", index.IndexCreate())
    manager.add_command("index-build", index.IndexBuild())
    manager.add_command("index-update", index.IndexUpdate())
    manager.add_command("index-destroy", index.IndexDestroy())
    manager.add_command("index-move", index.IndexMove())
    manager.add_command("index-optimize", index.IndexOptimize())
    manager.add_command("index-dump", index.IndexDump())
    from moin.scripts.maint import serialization
    manager.add_command("save", serialization.Serialize())
    manager.add_command("load", serialization.Deserialize())
    manager.add_command("load-sample", serialization.LoadSample())
    from moin.scripts.maint.dump_html import Dump
    manager.add_command("dump-html", Dump())
    from moin.scripts.account.create import Create_User
    manager.add_command("account-create", Create_User())
    from moin.scripts.account.disable import Disable_User
    manager.add_command("account-disable", Disable_User())
    from moin.scripts.account.resetpw import Set_Password
    manager.add_command("account-password", Set_Password())
    from moin.scripts.maint.reduce_revisions import Reduce_Revisions
    manager.add_command("maint-reduce-revisions", Reduce_Revisions())
    from moin.scripts.maint.set_meta import Set_Meta
    manager.add_command("maint-set-meta", Set_Meta())
    from moin.scripts.maint import modify_item
    manager.add_command("item-get", modify_item.GetItem())
    manager.add_command("item-put", modify_item.PutItem())
    from moin.scripts.migration.moin19.import19 import ImportMoin19
    manager.add_command("import19", ImportMoin19())

    from moin.scripts.maint.moinshell import MoinShell
    manager.add_command("shell", MoinShell())

    return manager.run(default_command=default_command)


def fatal(msg):
    sys.exit(msg)
