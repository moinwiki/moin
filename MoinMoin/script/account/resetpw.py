# Copyright: 2006-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - set a user password
"""


from flask import current_app as app
from flask import g as flaskg
from flask.ext.script import Command, Option

from MoinMoin import user
from MoinMoin.app import before_wiki


class Set_Password(Command):
    description = 'This command allows you to set a user password.'
    option_list = (
        Option('--name', '-n', required=False, dest='name', type=unicode,
               help='Set password for the user with user name NAME.'),
        Option('--uid', '-u', required=False, dest='uid', type=unicode,
               help='Set password for the user with user id UID.'),
        Option('--password', '-p', required=True, dest='password', type=unicode,
               help='New password for this account.'),
    )

    def run(self, name, uid, password):
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

        try:
            u.enc_password = app.cfg.cache.pwd_context.encrypt(password)
        except (TypeError, ValueError) as err:
            print "Error: Password could not get processed, aborting."
        else:
            u.save()
            print 'Password set.'
