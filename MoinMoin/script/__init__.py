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
    from flaskext.script import Manager, Server

    manager = Manager(create_app)
    manager.add_option('-c', '--config', dest='config', required=False, default=wiki_config)
    manager.add_command("moin", Server(host='127.0.0.1', port=8080))

    from MoinMoin.script.maint.index import IndexOperations
    manager.add_command("index", IndexOperations())
    from MoinMoin.script.account.create import Create_User
    manager.add_command("account_create", Create_User())
    from MoinMoin.script.account.disable import Disable_User
    manager.add_command("account_disable", Disable_User())
    from MoinMoin.script.account.resetpw import Set_Password
    manager.add_command("account_password", Set_Password())
    from MoinMoin.script.maint.reduce_revisions import Reduce_Revisions
    manager.add_command("maint_reduce_revisions", Reduce_Revisions())
    from MoinMoin.script.maint.set_meta import Set_Meta
    manager.add_command("maint_set_meta", Set_Meta())
    from MoinMoin.script.maint.create_item import Create_Item
    manager.add_command("maint_create_item", Create_Item())
    from MoinMoin.script.maint.modified_systemitems import Modified_SystemItems
    manager.add_command("maint_modified_systemitems", Modified_SystemItems())
    from MoinMoin.script.maint.xml import XML
    manager.add_command("maint_xml", XML())

    return manager.run(default_command=default_command)


def fatal(msg):
    sys.exit(msg)

