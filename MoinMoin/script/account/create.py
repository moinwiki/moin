# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - create a user account
"""


from flask.ext.script import Command, Option

from MoinMoin import user
from MoinMoin.app import before_wiki


class Create_User(Command):
    description = 'This command allows you to create a user account'
    option_list = (
        Option('--name', '-n', required=True, dest='name', type=unicode,
               help="Set the wiki user name to NAME."),
        Option('--display_name', '-d', required=False, dest="display_name", type=unicode,
               help="Set the wiki user's display name to DISPLAY_NAME (e.g. in case the NAME is cryptic)."),
        Option('--email', '-e', required=True, dest='email', type=unicode,
               help="Set the user's email address to EMAIL."),
        Option('--openid', '-o', required=False, dest='openid', type=unicode,
               help="Set the user's openid address."),
        Option('--password', '-p', required=True, dest="password", type=unicode,
               help="Set the user's password to PASSWORD."),
    )

    def run(self, name, display_name, email, openid, password):
        before_wiki()
        msg = user.create_user(username=name,
                               password=password,
                               email=email,
                               openid=openid)

        if msg:
            print msg
        else:
            u = user.User(auth_username=name)
            print " %-20s %-25s %-35s - created." % (u.itemid, u.name, u.email),
