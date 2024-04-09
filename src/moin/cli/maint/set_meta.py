# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Set Metadata of a revision

This script duplicates the last revision of the selected item
and sets or removes metadata.
"""


from ast import literal_eval

import sys
import click
from flask import current_app as app
from flask import g as flaskg
from flask.cli import FlaskGroup

from whoosh.query import Every

from moin.app import create_app
from moin.constants.keys import NAME, NAME_EXACT, REVID, REV_NUMBER, PARENTID

from moin import log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("maint-set-meta", help="Set meta data of a new revision")
@click.option("--key", "-k", required=False, type=str, help="The key you want to set/change in the new revision")
@click.option("--value", "-v", type=str, help="The value to set for the given key.")
@click.option(
    "--remove",
    "-r",
    is_flag=True,
    required=False,
    default=False,
    help="If you want to delete the key given, add this flag.",
)
@click.option(
    "--query", "-q", type=str, default="", help="Only perform the operation on items found by the given query."
)
def SetMeta(key, value, remove, query):
    logging.info("Set meta started")
    flaskg.add_lineno_attr = False
    if not ((key and value) or (key and remove)) or (key and value and remove):
        sys.exit(
            "You need to either specify a proper key/value pair or " "only a key you want to delete (with -r set)."
        )

    if not remove:
        try:
            value = literal_eval(value)
        except ValueError:
            sys.exit("You need to specify a valid Python literal as the argument")

    if query:
        qp = app.storage.query_parser([NAME_EXACT])
        q = qp.parse(query)
    else:
        q = Every()

    for current_rev in app.storage.search(q, limit=None):
        name = current_rev.meta[NAME]
        newmeta = dict(current_rev.meta)
        if remove:
            newmeta.pop(key)
            print(f"Processing {name!r}, removing {key}.")
        else:
            newmeta[key] = value
            print(f"Processing {name!r}, setting {key}={value!r}.")
        del newmeta[REVID]
        newmeta[REV_NUMBER] += 1
        newmeta[PARENTID] = current_rev.meta[REVID]
        current_rev.item.store_revision(newmeta, current_rev.data)
    logging.info("Set meta finished")
