# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - set a user password
"""


from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin import user


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

        u.enc_password = user.encodePassword(password)
        u.save()
        print 'Password set.'

