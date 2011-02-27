# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - disable a user account
"""


from flask import flaskg
from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin import user


class Disable_User(Command):
    description = 'This command allows you to disable user accounts.'
    option_list = (
        Option('--name', '-n', required=False, dest='name', type=unicode,
               help='Disable the user with user name NAME.'),
        Option('--uid', '-u', required=False, dest='uid', type=unicode,
               help='Disable the user with user id UID.'),
    )

    def run(self, name, uid):
        flaskg.unprotected_storage = app.unprotected_storage
        flags_given = name or uid
        if not flags_given:
            print 'incorrect number of arguments'
            import sys
            sys.exit()

        if uid:
            u = user.User(uid)
        elif name:
            uid = user.getUserId(name)
            u = user.User(uid)

        if not u.exists():
            print 'This user "%s" does not exists!' % u.name
            return

        print " %-20s %-25s %-35s" % (u.id, u.name, u.email),
        if not u.disabled: # only disable once
            u.disabled = 1
            u.name = "%s-%s" % (u.name, u.id)
            if u.email:
                u.email = "%s-%s" % (u.email, u.id)
            u.subscribed_items = [] # avoid using email
            u.save()
            print "- disabled."
        else:
            print "- is already disabled."

