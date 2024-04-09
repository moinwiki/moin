# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2011 MoinMoin:ReimarBauer
# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2012 MoinMoin:CheerXiao
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - Reduce Item Revisions

This script removes all revisions but the last one from all selected items.
"""

import click

from flask import current_app as app
from flask import g as flaskg
from flask.cli import FlaskGroup

from whoosh.query import Term, And, Regex, Not

from moin.constants.keys import NAME, NAME_SORT, NAME_EXACT, NAMESPACE, REVID, WIKINAME, PARENTID, REV_NUMBER, MTIME
from moin.constants.namespaces import NAMESPACE_USERPROFILES
from moin.app import create_app, before_wiki

from moin import log

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("maint-reduce-revisions", help="Remove all revisions but the last one from all selected items.")
@click.option(
    "--query", "-q", type=str, default="", help="Only perform the operation on items found by the given query."
)
@click.option(
    "--namespace",
    "-n",
    type=str,
    default="",
    help='Limit selection to a namespace; use "default" for default namespace.',
)
@click.option("--test", "-t", type=bool, default=0, help="List selected items, but do not update.")
def ReduceRevisions(query, namespace, test):
    logging.info("Reduce revisions started")
    before_wiki()
    q = And([Term(WIKINAME, app.cfg.interwikiname), Not(Term(NAMESPACE, NAMESPACE_USERPROFILES))])
    if query or namespace:
        if query:
            q = And([q, Regex(NAME_EXACT, query)])
        if namespace:
            if namespace == "default":
                namespace = ""
            q = And([q, Term(NAMESPACE, namespace)])
    else:
        q = Not(Term(NAMESPACE, NAMESPACE_USERPROFILES))

    for current_rev in app.storage.search(q, limit=None, sortedby=[NAMESPACE, NAME_SORT]):
        current_name = current_rev.meta[NAME]
        current_revid = current_rev.meta[REVID]
        current_namespace = current_rev.meta[NAMESPACE]
        current_revno = current_rev.meta[REV_NUMBER]
        current_full_name = current_namespace + "/" + current_name[0] if current_namespace else current_name
        if test:
            print(
                "Item named {!r} selected but not updated, has {} revisions :".format(current_full_name, current_revno)
            )
        else:
            print(f"Destroying historical revisions of {current_full_name!r}:")
            has_historical_revision = False
            for rev in current_rev.item.iter_revs():
                revid = rev.meta[REVID]
                if revid == current_revid:
                    # fixup metadata and overwrite existing revision; modified time will be updated if changed
                    changed = False
                    meta = dict(rev.meta)
                    if REV_NUMBER in meta and meta[REV_NUMBER] > 1 or REV_NUMBER not in meta:
                        changed = True
                        meta[REV_NUMBER] = 1
                    if PARENTID in meta:
                        changed = True
                        del meta[PARENTID]
                    if changed:
                        # By default store_revision and whoosh will replace mtime with current time making
                        # global history useless.
                        # Save existing mtime which has time this revision's data was last modified.
                        flaskg.data_mtime = meta[MTIME]
                        current_rev.item.store_revision(meta, current_rev.data, overwrite=True)
                        print("    (current rev meta data updated)")
                    continue
                has_historical_revision = True
                name = rev.meta[NAME]
                if name == current_name:
                    print(f"    Destroying revision {revid}")
                else:
                    print(f"    Destroying revision {revid} (named {name!r})")
                current_rev.item.destroy_revision(revid)
            if not has_historical_revision:
                print("    (no historical revisions)")

    logging.info("Reduce revisions finished")
