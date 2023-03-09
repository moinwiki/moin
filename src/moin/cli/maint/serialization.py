# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - backend serialization / deserialization
"""

import sys
import os
import click

from flask import current_app as app
from flask.cli import FlaskGroup

from moin.storage.middleware.serialization import serialize, deserialize
from moin.app import create_app

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


@cli.command('save', help='Serialize the backend into a file')
@click.option('--file', '-f', type=str, required=False,
              help='Filename of the output file.')
@click.option('--backends', '-b', type=str, required=False,
              help='Backend names to serialize (comma separated).')
@click.option('--all-backends', '-a', default=False,
              help='Serialize all configured backends.')
def Serialize(file=None, backends=None, all_backends=False):
    logging.info("Backup started")
    if file is None:
        f = sys.stdout
    else:
        f = open(file, "wb")
    with f as f:
        existing_backends = set(app.cfg.backend_mapping)
        if all_backends:
            backends = set(app.cfg.backend_mapping)
        elif backends:
            backends = set(backends.split(','))
        if backends:
            # low level - directly serialize some backend contents -
            # this does not use the index:
            if backends.issubset(existing_backends):
                for backend_name in backends:
                    backend = app.cfg.backend_mapping.get(backend_name)
                    serialize(backend, f)
            else:
                print("Error: Wrong backend name given.")
                print("Given Backends: %r" % backends)
                print("Configured Backends: %r" % existing_backends)
    logging.info("Backup finished")


@cli.command('load', help='Deserialize a file into the backend; with options to rename or remove a namespace')
@click.option('--file', '-f', type=str, required=True,
              help='Filename of the input file.')
@click.option('--new-ns', '-n', type=str, required=False, default=None,
              help='New namespace name to receive items from the old namespace name.')
@click.option('--old-ns', '-o', type=str, required=False, default=None,
              help='Old namespace that will be deleted, all items to be restored to new namespace.')
@click.option('--kill-ns', '-k', type=str, required=False, default=None,
              help='Namespace name to be deleted, no items within this namespace will be loaded.')
def Deserialize(file=None, new_ns=None, old_ns=None, kill_ns=None):
    logging.info("Load backup started")
    with open_file(file, "rb") as f:
        deserialize(f, app.storage.backend, new_ns=new_ns, old_ns=old_ns, kill_ns=kill_ns)
    logging.info("Load Backup finished. You need to run index-build now.")


@cli.command('load-sample', help='Load wiki sample items')
def LoadSample():
    logging.info("Load sample data started")
    dir_path = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(dir_path, '../../contrib/sample-backup.moin')
    filename = os.path.normpath(filename)
    with open_file(filename, "rb") as f:
        deserialize(f, app.storage.backend)
    logging.info("Load sample data finished. You need to run index-build now.")
