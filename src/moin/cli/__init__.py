# Copyright: 2000-2002 Juergen Hermann <jh@web.de>
# Copyright: 2006,2011 MoinMoin:ThomasWaldmann
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Extension Script Package
"""

import click
import sys

from flask.cli import FlaskGroup

from moin.app import create_app
from moin.cli.maint import create_instance, index, modify_item, set_meta, serialization, reduce_revisions, dump_html
from moin.cli.account import create, disable, resetpw
from moin.cli.migration.moin19 import import19

from moin import log

logging = log.getLogger(__name__)


def Help():
    """Moin initial help"""
    print(
        """\
Quick help / most important commands overview:

  moin create-instance  # Create wikiconfig and wiki instance directories

  moin index-create     # Create empty indexes and storage

  moin run              # Run moin's builtin web server

  moin import19         # Import wiki data from moin 1.9


For more information please run:

  moin --help

  moin <subcommand> --help

or read the Docs at https://moin-20.readthedocs.io/
"""
    )


# @click.option('--config', required=False, default=None)
@click.group(cls=FlaskGroup, create_app=create_app, invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Moin extensions to the Flask CLI"""
    logging.debug("invoked_subcommand: %s", ctx.invoked_subcommand)
    if ctx.invoked_subcommand is None:
        Help()
    sys.stdout.reconfigure(encoding="utf-8")


@cli.command("help", help="Quick help")
def _Help():
    Help()


cli.add_command(create_instance.cli_CreateInstance)
cli.add_command(create_instance.cli_BuildInstance)

cli.add_command(index.cli_IndexCreate)
cli.add_command(index.IndexBuild)
cli.add_command(index.IndexUpdate)
cli.add_command(index.IndexDestroy)
cli.add_command(index.IndexMove)
cli.add_command(index.cli_IndexOptimize)
cli.add_command(index.IndexDump)

cli.add_command(serialization.Serialize)
cli.add_command(serialization.Deserialize)

cli.add_command(dump_html.Dump)

cli.add_command(create.CreateUser)
cli.add_command(disable.DisableUser)
cli.add_command(resetpw.SetPassword)

cli.add_command(reduce_revisions.ReduceRevisions)

cli.add_command(set_meta.SetMeta)

cli.add_command(modify_item.cli_GetItem)
cli.add_command(modify_item.cli_PutItem)
cli.add_command(modify_item.cli_LoadHelp)
cli.add_command(modify_item.DumpHelp)
cli.add_command(modify_item.cli_LoadWelcome)
cli.add_command(modify_item.cli_ValidateMetadata)

cli.add_command(import19.ImportMoin19)
