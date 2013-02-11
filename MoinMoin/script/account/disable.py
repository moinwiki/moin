# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - disable a user account
"""


from flask.ext.script import Command, Option

from MoinMoin import user
from MoinMoin.app import before_wiki


class Disable_User(Command):
    description = 'This command allows you to disable user accounts.'
    option_list = (
        Option('--name', '-n', required=False, dest='name', type=unicode,
               help='Disable the user with user name NAME.'),
        Option('--uid', '-u', required=False, dest='uid', type=unicode,
               help='Disable the user with user id UID.'),
    )

    def run(self, name, uid):
        flags_given = name or uid
        if not flags_given:
            print 'incorrect number of arguments'
            import sys
            sys.exit()

        before_wiki()
        if uid:
            u = user.User(uid)
        elif name:
            u = user.User(auth_username=name)

        if not u.exists():
            print 'This user "{0!r}" does not exists!'.format(u.name)
            return

        print " {0:<20} {1:!r<25} {2:<35}".format(u.itemid, u.name, u.email),
        if not u.disabled:  # only disable once
            u.disabled = 1
            u.name = u"{0}-{1}".format(u.name, u.id)
            if u.email:
                u.email = u"{0}-{1}".format(u.email, u.id)
            u.subscribed_items = []  # avoid using email
            u.save()
            print "- disabled."
        else:
            print "- is already disabled."
