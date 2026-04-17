# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin project
# Copyright: 2026 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - CLI command to validate/repair item metadata.
"""

import click

from collections import defaultdict
from dataclasses import dataclass, field

from flask.cli import FlaskGroup

from moin import current_app, flaskg
from moin.app import create_app
from moin.cli._util import get_backends
from moin.constants.keys import (
    ITEMID,
    REVID,
    PARENTID,
    REV_NUMBER,
    MTIME,
)
from moin.constants.namespaces import NAMESPACE_USERPROFILES
from moin.log import getLogger
from moin.storage.middleware.serialization import get_rev_str, correcting_rev_iter

logger = getLogger(__name__)


@dataclass
class RevData:
    """
    Class for storing data used to correct rev_number and parentid.
    """
    rev_id: str
    rev_number: int
    mtime: int
    parent_id: str | None = None
    issues: list[str] = field(default_factory=list)


def _fix_if_bad(bad, meta, data, bad_revids, fix, backend):
    if bad:
        bad_revids.add(meta[REVID])
        if MTIME in meta:
            meta.pop(MTIME)  # store_revision adds the current timestamp
        if fix:
            try:
                item = current_app.storage.get_item(itemid=meta[ITEMID])
                rev = item.get_revision(meta[REVID])
                dict(rev.meta)  # force load to validate rev is in index
            except KeyError:
                logger.warning(f"bad revision not found in index {get_rev_str(meta)}")
                backend.store(meta, data)
            else:
                item.store_revision(meta, data, overwrite=True, trusted=True)


def ValidateMetadata(
    backend_names: str | None = None, all_backends: bool = False, verbose: bool = False, fix: bool = False
) -> set[str]:
    flaskg.add_lineno_attr = False
    backends = get_backends(backend_names, all_backends)
    bad_revids: set[str] = set()
    for backend in backends:
        revs: dict[str, list[RevData]] = defaultdict(list)
        for meta, data, issues in correcting_rev_iter(backend):
            revs[meta[ITEMID]].append(
                RevData(meta[REVID], meta.get(REV_NUMBER, -1), meta.get(MTIME, -1), meta.get(PARENTID))
            )
            bad = len(issues) > 0
            if verbose:
                for issue in issues:
                    print(issue)
            _fix_if_bad(bad, meta, data, bad_revids, fix, backend)

        # Skipping checks for userprofiles, as revision numbers and parentids are not used here
        if backend == current_app.cfg.backend_mapping[NAMESPACE_USERPROFILES]:
            continue

        # fix bad parentid references and repeated or missing revision numbers
        for item_id, rev_datum in revs.items():
            rev_datum.sort(key=lambda r: (r.rev_number, r.mtime))
            prev_rev_data = None
            for rev_data in rev_datum:
                if prev_rev_data is None:
                    if rev_data.parent_id:
                        rev_data.issues.append("parentid_error")
                        rev_data.parent_id = None
                    if rev_data.rev_number == -1:
                        rev_data.issues.append("revision_number_error")
                        rev_data.rev_number = 1
                else:  # prev_rev_data is not None
                    if rev_data.parent_id != prev_rev_data.rev_id:
                        rev_data.parent_id = prev_rev_data.rev_id
                        rev_data.issues.append("parentid_error")
                    if rev_data.rev_number <= prev_rev_data.rev_number:
                        rev_data.rev_number = prev_rev_data.rev_number + 1
                        rev_data.issues.append("revision_number_error")
                prev_rev_data = rev_data

            for rev_data in [r for r in rev_datum if r.issues]:
                bad = True
                meta, data = backend.retrieve(rev_data.rev_id)
                rev_str = get_rev_str(meta)
                if verbose:
                    for issue in rev_data.issues:
                        if issue == "parentid_error":
                            print(
                                f"{issue} {rev_str} meta_parentid: {meta.get(PARENTID)} "
                                f"correct_parentid: {rev_data.parent_id} "
                                f"meta_revision_number: {meta.get(REV_NUMBER)}"
                            )
                        else:  # issue == 'revision_number_error'
                            print(
                                f"{issue} {rev_str} meta_revision_number: {meta.get(REV_NUMBER)} "
                                f"correct_revision_number: {rev_data.rev_number}"
                            )
                if rev_data.parent_id:
                    meta[PARENTID] = rev_data.parent_id
                else:
                    try:
                        del meta[PARENTID]
                    except KeyError:
                        pass
                meta[REV_NUMBER] = rev_data.rev_number
                _fix_if_bad(bad, meta, data, bad_revids, fix, backend)

    print(f'{len(bad_revids)} items with invalid metadata found{" and fixed" if fix else ""}')
    return bad_revids


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("maint-validate-metadata", help="Find and optionally fix issues with item metadata")
@click.option("--backends", "-b", type=str, required=False, help="Backend names to serialize (comma separated).")
@click.option("--all-backends", "-a", is_flag=True, help="Serialize all configured backends.")
@click.option("--verbose/--no-verbose", "-v", default=False, help="Display detailed list of invalid metadata.")
@click.option("--fix/--no-fix", "-f", default=False, help="Fix invalid data.")
def cli_ValidateMetadata(backends=None, all_backends=False, verbose=False, fix=False):
    ValidateMetadata(backends, all_backends, verbose, fix)
