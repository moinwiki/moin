# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - backend serialization / deserialization
"""

import sys
import click

from flask import current_app as app
from flask.cli import FlaskGroup

from moin.storage.middleware.serialization import serialize, deserialize
from moin.app import create_app
from moin.cli._util import get_backends, drop_and_recreate_index

from moin import log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


def open_file(filename, mode):
    if filename is None:
        # Guess the IO stream from the mode:
        if "a" in mode or "w" in mode:
            stream = sys.stdout
        elif "r" in mode:
            stream = sys.stdin
        else:
            raise ValueError("Invalid mode string. Must contain 'r', 'w' or 'a'")

        # On Windows force the stream to be in binary mode if it's needed.
        if sys.platform == "win32" and "b" in mode:
            import os
            import msvcrt

            msvcrt.setmode(stream.fileno(), os.O_BINARY)

        f = stream
    else:
        f = open(filename, mode)
    return f


@cli.command("save", help="Serialize the backend into a file")
@click.option("--file", "-f", type=str, required=False, help="Filename of the output file.")
@click.option("--backends", "-b", type=str, required=False, help="Backend names to serialize (comma separated).")
@click.option("--all-backends", "-a", is_flag=True, help="Serialize all configured backends.")
def Serialize(file=None, backends=None, all_backends=False):
    logging.info("Backup started")
    if file is None:
        f = sys.stdout.buffer
    else:
        f = open(file, "wb")
    with f as f:
        backends = get_backends(backends, all_backends)
        for backend in backends:
            # low level - directly serialize some backend contents -
            # this does not use the index:
            serialize(backend, f)
    logging.info("Backup finished")


@cli.command("load", help="Deserialize a file into the backend; with options to rename or remove a namespace")
@click.option("--file", "-f", type=str, required=True, help="Filename of the input file.")
@click.option(
    "--new-ns",
    "-n",
    type=str,
    required=False,
    default=None,
    help="New namespace name to receive items from the old namespace name.",
)
@click.option(
    "--old-ns",
    "-o",
    type=str,
    required=False,
    default=None,
    help="Old namespace that will be deleted, all items to be restored to new namespace.",
)
@click.option(
    "--kill-ns",
    "-k",
    type=str,
    required=False,
    default=None,
    help="Namespace name to be deleted, no items within this namespace will be loaded.",
)
def Deserialize(file=None, new_ns=None, old_ns=None, kill_ns=None):
    logging.info("Load backup started")
    with open_file(file, "rb") as f:
        deserialize(f, app.storage.backend, new_ns=new_ns, old_ns=old_ns, kill_ns=kill_ns)
    logging.info("Rebuilding the index ...")
    drop_and_recreate_index(app.storage)
    logging.info("Load Backup finished.")
