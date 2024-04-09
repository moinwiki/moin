# Copyright: 2006-2013 MoinMoin:ThomasWaldmann
# Copyright: 2008 MoinMoin:JohannesBerg
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - set a user password
"""

import sys
import click

from flask import current_app as app
from flask.cli import FlaskGroup

from moin.constants.keys import ITEMID, NAME, NAME_EXACT, EMAIL, EMAIL_UNVALIDATED
from moin.app import create_app, before_wiki
from moin import user, log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


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
                raise UserHasNoEMail(
                    "Notification was requested, but User profile does not have "
                    "a validated E-Mail address (name: %r id: %r)!" % (u.name, u.itemid)
                )
            mailok, msg = u.mail_password_recovery(subject=subject, text=text)
            if not mailok:
                raise MailFailed(msg)
    else:
        raise NoSuchUser("User does not exist (name: %r id: %r)!" % (u.name, u.id))


@cli.command("account-password", help="Set user passwords")
@click.option("--name", "-n", required=False, type=str, help="Set password for the user with user name NAME.")
@click.option("--uid", "-u", required=False, type=str, help="Set password for the user with user id UID.")
@click.option("--password", "-p", required=False, type=str, help="New password for this account.")
@click.option("--all-users", "-a", is_flag=True, required=False, default=False, help="Reset password for ALL users.")
@click.option(
    "--notify",
    "-N",
    is_flag=True,
    required=False,
    default=False,
    help="Notify user(s), send them an E-Mail with a password reset link.",
)
@click.option("--verbose", "-v", is_flag=True, required=False, default=False, help="Verbose operation")
@click.option("--subject", required=False, type=str, help="Subject text for the password reset notification E-Mail.")
@click.option(
    "--text",
    required=False,
    type=str,
    help="Template text for the password reset notification E-Mail. " "Default: use the builtin standard template",
)
@click.option(
    "--text-from-file",
    required=False,
    type=str,
    help="Read full template for the password reset notification E-Mail from the given file, "
    "overrides --text. Default: None",
)
@click.option(
    "--skip-invalid",
    is_flag=True,
    required=False,
    default=False,
    help="If a user's password hash is already invalid (pw is already reset), skip this user.",
)
def SetPassword(name, uid, password, all_users, notify, verbose, subject, text, text_from_file, skip_invalid):
    flags_given = name or uid or all_users
    if not flags_given:
        print("incorrect number of arguments")
        sys.exit(1)

    if notify and not app.cfg.mail_enabled:
        print("This wiki is not enabled for mail processing. The --notify option requires this. Aborting...")
        sys.exit(1)

    if text_from_file:
        with open(text_from_file) as f:
            text = f.read().decode("utf-8")

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
    if not total:
        raise NoSuchUser("User not found.")

    logging.debug("Number of users found: %s", format(str(total)))
    for nr, (uid, meta) in enumerate(uids_metas, start=1):
        name = meta[NAME]
        email = meta.get(EMAIL)
        if email is None:
            email = meta.get(EMAIL_UNVALIDATED)
            if email is None:
                raise ValueError(
                    "neither EMAIL nor EMAIL_UNVALIDATED key is present in "
                    "user profile metadata of uid %r name %r" % (uid, name)
                )
            email += "[email_unvalidated]"
        try:
            set_password(uid, password, notify=notify, skip_invalid=skip_invalid, subject=subject, text=text)
        except Fault as err:
            status = "FAILURE: [%s]" % str(err)
        else:
            status = "SUCCESS"
        if verbose:
            print("uid %s, name %s, email %s (%05d / %05d) %s" % (uid, name, email, nr, total, status))
