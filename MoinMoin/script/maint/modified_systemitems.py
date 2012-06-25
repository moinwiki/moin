# Copyright: 2004 Nir Soffer <nirs@freeshell.org>
# Copyright: 2008,2011 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - list system items that has been edited in this wiki.

"""


from flask import current_app as app
from flaskext.script import Command
from MoinMoin.config import IS_SYSITEM, SYSITEM_VERSION
from MoinMoin.storage.error import NoSuchRevisionError

class Modified_SystemItems(Command):
    description = 'This command can be used to list system items that has been edited in this wiki.'

    def run(self):
        storage = app.unprotected_storage
        edited_sys_items = []
        for item in storage.iteritems():
            try:
                rev = item.get_revision(-1)
            except NoSuchRevisionError:
                continue
            is_sysitem = rev.get(IS_SYSITEM, False)
            if is_sysitem:
                version = rev.get(SYSITEM_VERSION)
                if version is None:
                    # if we don't have the version, it was edited:
                    edited_sys_items.append(item.name)

        # Format as numbered list, sorted by item name
        edited_sys_items.sort()
        if edited_sys_items:
            print "Edited system items:"
            for item_name in edited_sys_items:
                print item_name
        else:
            print "Not any modified system items found!"
