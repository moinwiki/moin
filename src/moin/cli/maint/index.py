# Copyright: 2011 MoinMoin:MichaelMayorov
# Copyright: 2023-2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - manage whoosh indexes (building, updating, (re)moving and displaying)
"""


import click
from flask import current_app as app
from flask import g as flaskg
from flask.cli import FlaskGroup

from moin.app import create_app, init_backends
from moin.constants.keys import LATEST_REVS, ALL_REVS
from moin.utils.filesys import wiki_index_exists


from moin import log

logging = log.getLogger(__name__)

ERR_NO_INDEX = "Error: Wiki index does not exist."


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("index-create", help="Create empty indexes")
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
@click.option("-i", "--index-create", is_flag=True, required=False, default=False, help="(deprecated)")
@click.option("-s", "--storage-create", is_flag=True, required=False, default=False, help="(deprecated)")
def cli_IndexCreate(tmp, index_create, storage_create):
    if index_create:
        logging.info("options -i or --index-create are obsolete and will be ignored")
    if storage_create:
        logging.info("options -s or --storage-create are obsolete and will be ignored")
    return IndexCreate(tmp=tmp)


def IndexCreate(**kwargs):
    """
    Create empty indexes
    """
    if wiki_index_exists():
        logging.error("Error: wiki index exists. Please check and destroy index before running index-create")
        return False
    logging.info("Index creation started")
    init_backends(app, create_backend=True)
    tmp = kwargs.get("tmp")
    app.storage.create(tmp=tmp)
    logging.info("Index creation finished")
    return True


@cli.command("index-destroy", help="Destroy the indexes")
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
def IndexDestroy(tmp):
    if not wiki_index_exists():
        logging.error(ERR_NO_INDEX)
        raise SystemExit(1)
    logging.info("Index destroy started")
    app.storage.destroy(tmp=tmp)
    logging.info("Index destroy finished")


@cli.command("index-build", help="Build the indexes")
@click.option("--procs", "-p", required=False, type=int, default=1, help="Number of processors the writer will use.")
@click.option(
    "--limitmb",
    "-l",
    required=False,
    type=int,
    default=10,
    help="Maximum memory (in megabytes) each index-writer will use for the indexing pool.",
)
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
@click.option("--index-create", "-i", is_flag=True, required=False, default=False)
@click.option("--storage-create", "-s", is_flag=True, required=False, default=False)
def IndexBuild(tmp, procs, limitmb, **kwargs):
    if not wiki_index_exists():
        logging.error(f"{ERR_NO_INDEX} Run 'moin index-create' first.")
        raise SystemExit(1)
    logging.info("Index build started")
    flaskg.add_lineno_attr = False  # no need to add lineno attributes while building indexes
    app.storage.rebuild(tmp=tmp, procs=procs, limitmb=limitmb)
    logging.info("Index build finished")


@cli.command("index-update", help="Update the indexes")
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
def IndexUpdate(tmp):
    if not wiki_index_exists():
        logging.error(ERR_NO_INDEX)
        raise SystemExit(1)
    logging.info("Index update started")
    app.storage.update(tmp=tmp)
    logging.info("Index update started")


@cli.command("index-move", help="Move the indexes from the temporary to the normal location")
def IndexMove():
    logging.info("Index move started")
    app.storage.move_index()
    logging.info("Index move finished")


@cli.command("index-optimize", help="Optimize the indexes")
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
def cli_IndexOptimize(tmp):
    return IndexOptimize(tmp)


def IndexOptimize(tmp):
    """
    Optimize the indexes
    """
    if not wiki_index_exists():
        logging.error(ERR_NO_INDEX)
        raise SystemExit(1)
    logging.info("Index optimization started")
    app.storage.optimize_index(tmp=tmp)
    logging.info("Index optimization finished")


@cli.command("index-dump", help="Dump the indexes in readable form to stdout")
@click.option("--tmp", is_flag=True, required=False, default=False, help="use the temporary location.")
@click.option("--truncate/--no-truncate", default=True, help="truncate long entries")
def IndexDump(tmp, truncate):
    if not wiki_index_exists():
        logging.error(ERR_NO_INDEX)
        raise SystemExit(1)
    logging.info("Index dump started")
    for idx_name in [LATEST_REVS, ALL_REVS]:
        print(f" {'-' * 10} {idx_name} {'-' * 60}")
        for kvs in app.storage.dump(tmp=tmp, idx_name=idx_name):
            for k, v in kvs:
                v = repr(v)
                if truncate:
                    v = v[:70]
                print(k, v)
            print()
    logging.info("Index dump finished")
