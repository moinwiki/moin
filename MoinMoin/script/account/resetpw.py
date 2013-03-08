# Copyright: 2006-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - set a user password
"""


from flask.ext.script import Command, Option

from MoinMoin.constants.keys import ITEMID, NAME, NAME_EXACT, EMAIL
from MoinMoin import user
from MoinMoin.app import before_wiki


class Fault(Exception):
    """something went wrong"""


class NoSuchUser(Fault):
    """raised if no such user exists"""


class MailFailed(Fault):
    """raised if e-mail sending failed"""


def set_password(uid, password, notify=False):
    u = user.User(uid)
    if u and u.exists():
        u.set_password(password)
        u.save()
        if notify and not u.disabled and u.email:
            mailok, msg = u.mail_password_recovery()
            if not mailok:
                raise MailFailed(msg)
    else:
        raise NoSuchUser('User does not exist (name: %r id: %r)!' % (u.name, u.id))


class Set_Password(Command):
    description = 'This command allows you to set a user password.'
    option_list = (
        Option('--name', '-n', required=False, dest='name', type=unicode,
               help='Set password for the user with user name NAME.'),
        Option('--uid', '-u', required=False, dest='uid', type=unicode,
               help='Set password for the user with user id UID.'),
        Option('--password', '-p', required=False, dest='password', type=unicode,
               help='New password for this account.'),
        Option('--all-users', '-a', required=False, dest='all_users', action='store_true', default=False,
               help='Reset password for ALL users.'),
        Option('--notify', '-N', required=False, dest='notify', action='store_true', default=False,
               help='Notify user(s), send them an E-Mail with a password reset link.'),
        Option('--verbose', '-v', required=False, dest='verbose', action='store_true', default=False,
               help='Verbose operation'),
    )

    def run(self, name, uid, password, all_users, notify, verbose):
        flags_given = name or uid or all_users
        if not flags_given:
            print 'incorrect number of arguments'
            import sys
            sys.exit()

        before_wiki()
        if uid:
            query = {ITEMID: uid}
        elif name:
            query = {NAME_EXACT: name}
        elif all_users:
            query = {}

        # sorting the list so we have some specific, reproducable order
        uids_metas = sorted([(rev.meta[ITEMID], rev.meta) for rev in user.search_users(**query)])
        total = len(uids_metas)
        for nr, (uid, meta) in enumerate(uids_metas, start=1):
            name = meta[NAME]
            email = meta[EMAIL]
            try:
                set_password(uid, password, notify=notify)
            except Fault, err:
                status = "FAILURE: [%s]" % str(err)
            else:
                status = "SUCCESS"
            if verbose:
                print "uid %s, name %s, email %s (%05d / %05d) %s" % (uid, name, email, nr, total, status)
