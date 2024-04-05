# Copyright: 2006 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - create a user account
"""


import click
from flask.cli import FlaskGroup

from moin.app import create_app, before_wiki
from moin import user, log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
@click.pass_context
def cli():
    pass


@cli.command("account-create", help="Create a user account")
@click.option("-n", "--name", required=True, type=str, help="Set the wiki user name to NAME.")
@click.option("-e", "--email", required=True, type=str, help="Set the user's email address to EMAIL.")
@click.option("-p", "--password", required=True, type=str, help="Set the user's password to PASSWORD.")
@click.option(
    "-d",
    "--display-name",
    required=False,
    type=str,
    help="Set the wiki user's display name to DISPLAY_NAME (e.g. in case the NAME is cryptic).",
)
def CreateUser(name, display_name, email, password):
    """Create a new user account"""
    logging.debug("display_name: %s", str(display_name))
    before_wiki()

    # TODO: add display_name to create_user
    msg = user.create_user(username=name, password=password, email=email)

    if msg:
        print(msg)
    else:
        u = user.User(auth_username=name)
        logging.info("User %s %s %s - created.", u.itemid, u.name, u.email)
