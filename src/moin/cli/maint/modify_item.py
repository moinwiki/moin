# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - get an item revision from the wiki, put it back into the wiki.
"""

from collections import defaultdict
from dataclasses import dataclass, field
import json
import io
import os

import click
from flask import current_app as app
from flask import g as flaskg
from flask.cli import FlaskGroup

from moin.app import create_app, before_wiki
from moin.cli._util import get_backends
from moin.storage.middleware.serialization import get_rev_str, correcting_rev_iter
from moin.constants.namespaces import NAMESPACE_USERPROFILES
from moin.constants.keys import CURRENT, ITEMID, DATAID, NAMESPACE, WIKINAME, REVID, PARENTID, REV_NUMBER, MTIME, NAME
from moin.utils.interwiki import split_fqname
from moin.items import Item

from moin import log, help as moin_help

logging = log.getLogger(__name__)


def _get_path_to_help(subdir=""):
    help_path = os.path.dirname(moin_help.__file__)
    return os.path.normpath(os.path.join(help_path, subdir))


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("item-get", help="Get an item revision from the wiki")
@click.option("--name", "-n", type=str, required=True, help="Name of the item to get.")
@click.option(
    "--meta", "-m", "--meta_file", type=str, required=True, help="Filename of file to create for the metadata."
)
@click.option("--data", "-d", "--data_file", type=str, required=True, help="Filename of file to create for the data.")
@click.option(
    "--revid",
    "-r",
    type=str,
    required=False,
    default=CURRENT,
    help="Revision ID of the revision to get (default: current rev).",
)
@click.option("--crlf/--no-crlf", help="use windows line endings in output files")
def cli_GetItem(name, meta, data, revid, crlf):
    logging.info("Get item started")
    GetItem(name, meta, data, revid, "\r\n" if crlf else "\n")
    logging.info("Get item finished")


def GetItem(name, meta_file, data_file, revid, newline="\n"):
    """
    Get an item revision from the wiki and save meta and data in separate files.
    If this revision has alias names, return a list of all names, else return None.
    """
    fqname = split_fqname(name)
    item = app.storage.get_item(**fqname.query)
    rev = item[revid]
    alias_names = None if len(rev.meta[NAME]) < 2 else rev.meta[NAME]
    meta = json.dumps(dict(rev.meta), sort_keys=True, indent=2, ensure_ascii=False)
    with open(meta_file, "w", encoding="utf-8", newline=newline) as mf:
        mf.write(meta + "\n")
    if "charset" in rev.meta["contenttype"]:
        # input data will have \r\n line endings, output will have specified endings
        # those running on windows with git autocrlf=true will want --crlf
        # those running on linux or with autocrlf=input will want --no-crlf
        charset = rev.meta["contenttype"].split("charset=")[1]
        data = rev.data.read().decode(charset)
        lines = data.splitlines()
        # add trailing line ending which may have been removed by splitlines,
        # or add extra trailing line ending which will be removed in _PutItem if file is imported
        lines = "\n".join(lines) + "\n"
        with open(data_file, "w", encoding=charset, newline=newline) as df:
            df.write(lines)
        return alias_names

    data = rev.data.read()
    with open(data_file, "wb") as df:
        df.write(data)
    logging.info("Get item finished")
    return alias_names


@cli.command("item-put", help="Put an item revision into the wiki")
@click.option("--meta", "-m", "--meta-file", type=str, required=True, help="Filename of file to read as metadata.")
@click.option("--data", "-d", "--data-file", type=str, required=True, help="Filename of file to read as data.")
@click.option(
    "--overwrite", "-o", is_flag=True, default=False, help="If given, overwrite existing revisions, if requested."
)
def cli_PutItem(meta, data, overwrite):
    logging.info("Put item started")
    PutItem(meta, data, overwrite)
    logging.info("Put item finished")


def PutItem(meta_file, data_file, overwrite):
    """
    Put an item revision from file into the wiki
    """
    flaskg.add_lineno_attr = False
    with open(meta_file, "rb") as mf:
        meta = mf.read()
    meta = meta.decode("utf-8")
    meta = json.loads(meta)
    to_kill = [WIKINAME]  # use target wiki name
    for key in to_kill:
        meta.pop(key, None)
    if overwrite:
        # by default, indexing.py will update meta[MTIME] with current time making global history useless
        # we preserve the old modified time for use by indexing.py
        flaskg.data_mtime = meta[MTIME]
    else:
        # if we remove the REVID, it will create a new one and store under the new one
        meta.pop(REVID, None)
        meta.pop(DATAID, None)
    query = {ITEMID: meta[ITEMID], NAMESPACE: meta[NAMESPACE]}
    logging.debug(f"query: {str(query)}")
    item = app.storage.get_item(**query)

    # we want \r\n line endings in data out because \r\n is required in form textareas
    if "charset" in meta["contenttype"]:
        charset = meta["contenttype"].split("charset=")[1]
        with open(data_file, "rb") as df:
            data = df.read().decode(charset)
        if "\r\n" not in data and "\n" in data:
            data = data.replace("\n", "\r\n")
        data = data.encode(charset)
        if 0 < len(data) - meta["size"] <= 2:
            data = data[0 : meta["size"]]  # potentially truncate trailing newline added by _GetItem
        buffer = io.BytesIO()
        buffer.write(data)
        buffer.seek(0)
        item.store_revision(meta, buffer, overwrite=overwrite)
        buffer.close()
        return

    with open(data_file, "rb") as df:
        item.store_revision(meta, df, overwrite=overwrite)


@cli.command("load-help", help="Load a directory of help .data and .meta file pairs into a wiki namespace")
@click.option("--namespace", "-n", type=str, required=True, help="Namespace to be loaded: help-common, help-en, etc.")
@click.option("--path_to_help", "--path", "-p", type=str, help="Override source directory, default is src/moin/help")
def cli_LoadHelp(namespace, path_to_help):
    return LoadHelp(namespace, path_to_help)


def LoadHelp(namespace, path_to_help):
    """
    Load an entire help namespace from distribution source.
    """
    logging.info("Load help started")
    if path_to_help is None:
        path_to_help = _get_path_to_help()
    path_to_items = os.path.normpath(os.path.join(path_to_help, namespace))
    if not os.path.isdir(path_to_items):
        print(f"Abort: the {path_to_items} directory does not exist")
        return
    file_list = os.listdir(path_to_items)
    if len(file_list) == 0:
        print(f"Abort: the {path_to_items} directory is empty")
        return
    count = 0
    for f in file_list:
        if f.endswith(".meta"):
            # filenames must have / characters replaced with %2f, item will be saved with name(s) in metadata
            item_name = f[:-5].replace("%2f", "/")
            data_file = f.replace(".meta", ".data")
            meta_file = os.path.join(path_to_items, f)
            data_file = os.path.join(path_to_items, data_file)
            PutItem(meta_file, data_file, "true")
            print("Item loaded:", item_name)
            count += 1
    print(f"Success: help namespace {namespace} loaded successfully with {count} items")


@cli.command("dump-help", help="Dump a namespace of user help items to .data and .meta file pairs")
@click.option("--namespace", "-n", type=str, required=True, help="Namespace to be dumped: help-common, help-en, etc.")
@click.option("--path_to_help", "--path", "-p", type=str, help="Override output directory, default is src/moin/help")
@click.option("--crlf/--no-crlf", help="use windows line endings in output files")
def DumpHelp(namespace, path_to_help, crlf):
    """
    Save an entire help namespace to the distribution source.
    Items with alias names must be copied only once.
    """
    logging.info("Dump help started")
    before_wiki()
    if path_to_help is None:
        path_to_help = _get_path_to_help()
    # Item name is the name of the namespace, create a dummy item to get the list of files
    item = Item.create(namespace)
    # get_index is fast, but returns alias names as if they are unique items
    _, files = item.get_index()
    count = 0
    no_alias_dups = []
    for file_ in files:
        if file_.relname in no_alias_dups:
            continue
        # convert / characters to avoid invalid paths
        esc_name = file_.relname.replace("/", "%2f")
        meta_file = os.path.join(path_to_help, namespace, esc_name + ".meta")
        data_file = os.path.join(path_to_help, namespace, esc_name + ".data")
        alias_names = GetItem(str(file_.fullname), meta_file, data_file, CURRENT, "\r\n" if crlf else "\n")
        if alias_names:
            # no harm in adding current name to no_alias_dups
            no_alias_dups += alias_names
        print("Item dumped::", file_.relname)
        count += 1
    print(f"Success: help namespace {namespace} saved with {count} items")


@cli.command("maint-validate-metadata", help="Find and optionally fix issues with item metadata")
@click.option("--backends", "-b", type=str, required=False, help="Backend names to serialize (comma separated).")
@click.option("--all-backends", "-a", is_flag=True, help="Serialize all configured backends.")
@click.option("--verbose/--no-verbose", "-v", default=False, help="Display detailed list of invalid metadata.")
@click.option("--fix/--no-fix", "-f", default=False, help="Fix invalid data.")
def cli_ValidateMetadata(backends=None, all_backends=False, verbose=False, fix=False):
    ValidateMetadata(backends, all_backends, verbose, fix)


def _fix_if_bad(bad, meta, data, bad_revids, fix, backend):
    if bad:
        bad_revids.add(meta[REVID])
        if fix:
            try:
                item = app.storage.get_item(itemid=meta[ITEMID])
                rev = item.get_revision(meta[REVID])
                dict(rev.meta)  # force load to validate rev is in index
            except KeyError:
                logging.warning(f"bad revision not found in index {get_rev_str(meta)}")
                backend.store(meta, data)
            else:
                item.store_revision(meta, data, overwrite=True, trusted=True)


@dataclass
class RevData:
    """class for storing data used to correct rev_number and parentid"""

    rev_id: str
    rev_number: int
    mtime: int
    parent_id: str = None
    issues: list[str] = field(default_factory=list)


def ValidateMetadata(backends=None, all_backends=False, verbose=False, fix=False):
    flaskg.add_lineno_attr = False
    backends = get_backends(backends, all_backends)
    bad_revids = set()
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
        if backend == app.cfg.backend_mapping[NAMESPACE_USERPROFILES]:
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


@cli.command("welcome", help="Load initial welcome page into an empty wiki")
def cli_LoadWelcome():
    return LoadWelcome()


def LoadWelcome():
    """
    Load a welcome page as initial home from distribution source.
    """
    logging.info("Load welcome page started")
    path_to_items = _get_path_to_help("welcome")
    for name in ["Home", "users-Home"]:
        if app.storage.has_item(name):
            logging.warning("Item with name %s exists and will not be overwritten.", name)
        else:
            meta_file = os.path.join(path_to_items, f"{name}.meta")
            data_file = os.path.join(path_to_items, f"{name}.data")
            PutItem(meta_file, data_file, "true")
    logging.info("Load welcome finished")
