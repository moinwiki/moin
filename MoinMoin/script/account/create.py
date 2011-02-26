"""
MoinMoin - create a user account

@copyright: 2006 MoinMoin:ThomasWaldmann,
            2011 MoinMoin:ReimarBauer
@license: GNU GPL, see COPYING for details.
"""

from flask import flaskg
from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin import user


class Create_User(Command):
    description = 'This command allows you to create a user account'
    option_list = (
        Option('--name', '-n', required=True, dest='name', type=unicode,
               help="Set the wiki user name to NAME."),
        Option('--alias', '-a', required=False, dest="aliasname", type=unicode,
               help="Set the wiki user alias name to ALIAS (e.g. the real name if NAME is cryptic)."),
        Option('--email', '-e', required=True, dest='email', type=unicode,
               help="Set the user's email address to EMAIL."),
        Option('--openid', '-o', required=False, dest='openid', type=unicode,
               help="Set the user's openid address."),
        Option('--password', '-p', required=True, dest="password", type=unicode,
               help="Set the user's password to PASSWORD."),
    )

    def run(self, name, aliasname, email, openid, password):
        flaskg.unprotected_storage = app.unprotected_storage
        msg = user.create_user(username=name,
                               password=password,
                               email=email,
                               openid=openid)

        if msg:
            print msg
        else:
            uid = user.getUserId(name)
            u = user.User(uid)
            print " %-20s %-25s %-35s - created." % (u.id, u.name, u.email),

