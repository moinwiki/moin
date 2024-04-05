# Copyright: 2020 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Create a MoinMoin wiki instance.

Activate a moin virtual env, then run this command:

    moin create-instance --path /path/to/new/instance

If path is not specified, the CWD is used as a default.

If the path does not exist, directories are created.
If wikiconfig.py does not exist, it is copied from the venv config directory.
If intermap.txt does not exist, it is copied from the venv contrib directory.
If a wiki_local directory does not exist, it is created.

Next: CD to new instance directory, run this command to initialize storage and index

    moin index-create

Optionally, populate the empty wiki with additional commands

    moin load <options>
    moin import19 <options>
    moin load-help <options>
"""

import os
import shutil
import subprocess
import click

from flask.cli import FlaskGroup

from moin import config, contrib, log
from moin.app import create_app
from moin.cli.maint import index, modify_item

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("create-instance", help="Create wikiconfig and wiki instance directories and copy required files")
@click.option(
    "--full",
    "-f",
    required=False,
    is_flag=True,
    default=False,
    help="full setup including index creation and load of help data and welcome page",
)
@click.option(
    "--path", "-p", required=False, type=str, help="Path to new wikiconfig dir, defaults to CWD if not specified."
)
def cli_CreateInstance(full, path):
    return CreateInstance(full, path=path)


def CreateInstance(full, **kwargs):
    """
    Create wikiconfig and wiki instance directories and copy required files.
    """
    logging.debug("Instance creation started.")
    config_path = os.path.dirname(config.__file__)
    contrib_path = os.path.dirname(contrib.__file__)
    path = kwargs.get("path", None)
    if not path:
        path = os.getcwd()
    if os.path.exists(path):
        logging.info("Directory %s already exists, using as wikiconfig dir.", os.path.abspath(path))
    else:
        os.makedirs(path)
        logging.info("Directory %s created.", os.path.abspath(path))

    if os.path.isfile(os.path.join(path, "wikiconfig.py")):
        logging.info("wikiconfig.py already exists, not copied.")
    else:
        shutil.copy(os.path.join(config_path, "wikiconfig.py"), path)

    if os.path.isfile(os.path.join(path, "intermap.txt")):
        logging.info("intermap.txt already exists, not copied.")
    else:
        shutil.copy(os.path.join(contrib_path, "intermap.txt"), path)
    local_path = os.path.join(path, "wiki_local")
    if not os.path.isdir(local_path):
        os.mkdir(local_path)
    logging.info("Instance creation finished.")

    if full:
        if path != os.getcwd():
            os.chdir(path)
        subprocess.call("moin build-instance", shell=True)


@cli.command("build-instance", hidden=True)
def cli_BuildInstance():
    """
    Create and build index, load help data and welcome page.
    This command is hidden in help. For internal use in "create-instance --full" only!
    """
    logging.info("Build Instance started.")
    logging.debug("CWD: %s", os.getcwd())
    if index.IndexCreate():
        modify_item.LoadHelp(namespace="help-en", path_to_help=None)
        modify_item.LoadHelp(namespace="help-common", path_to_help=None)
        modify_item.LoadWelcome()
        index.IndexOptimize(tmp=False)
        logging.info("Full instance setup finished.")
        logging.info('You can now use "moin run" to start the builtin server.')
    else:
        logging.error("Build Instance failed.")
