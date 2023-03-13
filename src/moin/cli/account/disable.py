# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - disable a user account
"""


import click
from flask.cli import FlaskGroup  # , with_appcontext

from moin.app import create_app, before_wiki
from moin import user, log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command('account-disable', help='Disable user accounts')
@click.option('--name', '-n', required=False, type=str, help='Disable the user with user name NAME.')
@click.option('--uid', '-u', required=False, type=str, help='Disable the user with user id UID.')
def DisableUser(name, uid):
    flags_given = name or uid
    if not flags_given:
        print('incorrect number of arguments')
        import sys
        sys.exit()

    before_wiki()
    if uid:
        u = user.User(uid)
    elif name:
        u = user.User(auth_username=name)

    if not u.exists():
        print('This user "{0!r}" does not exists!'.format(u.name))
        return

    print(" {0:<20} {1!r:<25} {2:<35}".format(u.itemid, u.name, u.email), end=' ')
    if not u.disabled:  # only disable once
        u.disabled = True
        u.name = "{0}-{1}".format(u.name, u.itemid)
        if u.email:
            u.email = "{0}-{1}".format(u.email, u.itemid)
        u.subscriptions = []
        u.save(force=True)
        logging.info("User %s %s %s - disabled.", u.itemid, u.name, u.email)
    else:
        logging.info("User %s %s %s - is already disabled.", u.itemid, u.name, u.email)
