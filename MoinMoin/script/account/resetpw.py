# Copyright: 2006-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - set a user password
"""


import sys

from flask import current_app as app
from flask.ext.script import Command, Option

from MoinMoin.constants.keys import (
    ITEMID, NAME, NAME_EXACT, EMAIL, EMAIL_UNVALIDATED,
)
from MoinMoin import user
from MoinMoin.app import before_wiki


class Fault(Exception):
    """something went wrong"""


class NoSuchUser(Fault):
    """raised if no such user exists"""


class UserHasNoEMail(Fault):
    """raised if user has no e-mail address in his profile"""


class MailFailed(Fault):
    """raised if e-mail sending failed"""


def set_password(uid, password, notify=False, skip_invalid=False, subject=None, text=None):
    u = user.User(uid)
    if u and u.exists():
        if skip_invalid and u.has_invalidated_password():
            return
        u.set_password(password)
        u.save()
        if notify and not u.disabled:
            if not u.email:
                raise UserHasNoEMail('Notification was requested, but User profile does not have a validated E-Mail address (name: %r id: %r)!' % (u.name, u.itemid))
            mailok, msg = u.mail_password_recovery(subject=subject, text=text)
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
        Option('--subject', required=False, dest='subject', type=unicode,
               help='Subject text for the password reset notification E-Mail.'),
        Option('--text', required=False, dest='text', type=unicode,
               help='Template text for the password reset notification E-Mail. Default: use the builtin standard template'),
        Option('--text-from-file', required=False, dest='text_file', type=unicode,
               help='Read full template for the password reset notification E-Mail from the given file, overrides --text. Default: None'),
        Option('--skip-invalid', required=False, dest='skip_invalid', action='store_true',
               help='If a user\'s password hash is already invalid (pw is already reset), skip this user.'),
    )

    def run(self, name, uid, password, all_users, notify, verbose, subject, text, text_file, skip_invalid):
        flags_given = name or uid or all_users
        if not flags_given:
            print 'incorrect number of arguments'
            sys.exit(1)

        if notify and not app.cfg.mail_enabled:
            print "This wiki is not enabled for mail processing. The --notify option requires this. Aborting..."
            sys.exit(1)

        if text_file:
            with open(text_file) as f:
                text = f.read().decode('utf-8')

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
            email = meta.get(EMAIL)
            if email is None:
                email = meta.get(EMAIL_UNVALIDATED)
                if email is None:
                    raise ValueError("neither EMAIL nor EMAIL_UNVALIDATED key is present in user profile metadata of uid %r name %r" % (uid, name))
                else:
                    email += '[email_unvalidated]'
            try:
                set_password(uid, password, notify=notify, skip_invalid=skip_invalid,
                             subject=subject, text=text)
            except Fault as err:
                status = "FAILURE: [%s]" % str(err)
            else:
                status = "SUCCESS"
            if verbose:
                print "uid %s, name %s, email %s (%05d / %05d) %s" % (uid, name, email, nr, total, status)
