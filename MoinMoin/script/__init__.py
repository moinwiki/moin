# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006,2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Extension Script Package
"""

import sys


def main(default_command='moin', wiki_config=None):
    """
    console_script entry point
    """
    from MoinMoin.app import create_app
    from flask.ext.script import Manager, Server

    manager = Manager(create_app)
    manager.add_option('-c', '--config', dest='config', required=False, default=wiki_config)
    manager.add_option('-i', '--index-create', action='store_true', dest='create_index',
                       required=False, default=False)
    manager.add_option('-s', '--storage-create', action='store_true', dest='create_storage',
                       required=False, default=False)
    manager.add_command("moin", Server(host='127.0.0.1', port=8080))

    from MoinMoin.script.maint import index
    manager.add_command("index-create", index.IndexCreate())
    manager.add_command("index-build", index.IndexBuild())
    manager.add_command("index-update", index.IndexUpdate())
    manager.add_command("index-destroy", index.IndexDestroy())
    manager.add_command("index-move", index.IndexMove())
    manager.add_command("index-optimize", index.IndexOptimize())
    manager.add_command("index-dump", index.IndexDump())
    from MoinMoin.script.maint import serialization
    manager.add_command("save", serialization.Serialize())
    manager.add_command("load", serialization.Deserialize())
    from MoinMoin.script.account.create import Create_User
    manager.add_command("account-create", Create_User())
    from MoinMoin.script.account.disable import Disable_User
    manager.add_command("account-disable", Disable_User())
    from MoinMoin.script.account.resetpw import Set_Password
    manager.add_command("account-password", Set_Password())
    from MoinMoin.script.maint.reduce_revisions import Reduce_Revisions
    manager.add_command("maint-reduce-revisions", Reduce_Revisions())
    from MoinMoin.script.maint.set_meta import Set_Meta
    manager.add_command("maint-set-meta", Set_Meta())
    from MoinMoin.script.maint import modify_item
    manager.add_command("item-get", modify_item.GetItem())
    manager.add_command("item-put", modify_item.PutItem())
    from MoinMoin.script.maint.modified_systemitems import Modified_SystemItems
    manager.add_command("maint-modified-systemitems", Modified_SystemItems())
    from MoinMoin.script.migration.moin19.import19 import ImportMoin19
    manager.add_command("import19", ImportMoin19())

    from MoinMoin.script.maint.moinshell import MoinShell
    manager.add_command("shell", MoinShell())

    return manager.run(default_command=default_command)


def fatal(msg):
    sys.exit(msg)
