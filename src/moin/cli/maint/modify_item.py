# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin project
# Copyright: 2026 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - CLI commands to get an item revision from the wiki and put it back.
"""

from __future__ import annotations

from typing import cast

import json
import io
import os

import click

from flask.cli import FlaskGroup

from moin import current_app, flaskg
from moin import help as moin_help
from moin.app import create_app, before_wiki
from moin.log import getLogger
from moin.constants.keys import (
    CONTENTTYPE,
    CURRENT,
    ITEMID,
    DATAID,
    NAMESPACE,
    REVID,
    SIZE,
    MTIME,
    NAME,
)
from moin.utils.names import split_fqname
from moin.items import Item

logger = getLogger(__name__)


def _get_path_to_help(subdir: str = "") -> str:
    help_path = os.path.dirname(moin_help.__file__)
    return os.path.normpath(os.path.join(help_path, subdir))


def get_item(name: str, meta_file: str, data_file: str, revid: str, newline: str = "\n") -> list[str] | None:
    """
    Get an item revision from the wiki and save meta and data in separate files.
    If this revision has alias names, return a list of all names, else return None.
    """
    fqname = split_fqname(name)
    item = current_app.storage.get_item(**fqname.query)
    rev = item[revid]
    names = cast(list[str], rev.meta[NAME])

    alias_names = None if len(names) < 2 else names

    meta = json.dumps(dict(rev.meta), sort_keys=True, indent=2, ensure_ascii=False)
    with open(meta_file, "w", encoding="utf-8", newline=newline) as mf:
        mf.write(meta + "\n")

    content_type = rev.meta[CONTENTTYPE]
    assert isinstance(content_type, str)

    if "charset" in content_type:
        # Input data will have \r\n line endings; output will use the specified endings.
        # Those running on Windows with git autocrlf=true will want --crlf.
        # Those running on Linux or with autocrlf=input will want --no-crlf.
        charset = content_type.split("charset=")[1]
        data = rev.data.read().decode(charset)
        lines = data.splitlines()
        # add trailing line ending which may have been removed by splitlines,
        # or add extra trailing line ending which will be removed in PutItem if file is imported
        lines = "\n".join(lines) + "\n"
        with open(data_file, "w", encoding=charset, newline=newline) as df:
            df.write(lines)
    else:
        data = rev.data.read()
        with open(data_file, "wb") as df:
            df.write(data)

    logger.info("Get item finished")
    return alias_names


def put_item(meta_file: str, data_file: str, overwrite: bool) -> None:
    """
    Put an item revision from file into the wiki
    """
    flaskg.add_lineno_attr = False
    with open(meta_file, "rb") as mf:
        meta = mf.read()
    meta = meta.decode("utf-8")
    meta = json.loads(meta)
    if overwrite:
        # by default, indexing.py will update meta[MTIME] with current time making global history useless
        # we preserve the old modified time for use by indexing.py
        flaskg.data_mtime = meta[MTIME]
    else:
        # if we remove the REVID, it will create a new one and store under the new one
        meta.pop(REVID, None)
        meta.pop(DATAID, None)
    query = {ITEMID: meta[ITEMID], NAMESPACE: meta[NAMESPACE]}
    logger.debug(f"query: {str(query)}")
    item = current_app.storage.get_item(**query)

    # we want \r\n line endings in data out because \r\n is required in form textareas
    if "charset" in meta[CONTENTTYPE]:
        charset = meta[CONTENTTYPE].split("charset=")[1]
        with open(data_file, "rb") as df:
            data = df.read().decode(charset)
        if "\r\n" not in data and "\n" in data:
            data = data.replace("\n", "\r\n")
        data = data.encode(charset)
        if 0 < len(data) - meta[SIZE] <= 2:
            data = data[0 : meta[SIZE]]  # potentially truncate trailing newline added by _GetItem
        buffer = io.BytesIO()
        buffer.write(data)
        buffer.seek(0)
        item.store_revision(meta, buffer, overwrite=overwrite)
        buffer.close()
    else:
        with open(data_file, "rb") as df:
            item.store_revision(meta, df, overwrite=overwrite)


def load_welcome() -> None:
    """
    Load a welcome page as initial home from distribution source.
    """
    logger.info("Load welcome page started")
    path_to_items = _get_path_to_help("welcome")
    for name in ["Home", "users-Home"]:
        if current_app.storage.has_item(name):
            logger.warning("Item with name %s exists and will not be overwritten.", name)
        else:
            meta_file = os.path.join(path_to_items, f"{name}.meta")
            data_file = os.path.join(path_to_items, f"{name}.data")
            put_item(meta_file, data_file, True)
    logger.info("Load welcome finished")


def load_help(namespace: str, path_to_help: str) -> None:
    """
    Load an entire help namespace from distribution source.
    """
    logger.info("Load help started")
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
            put_item(meta_file, data_file, True)
            print("Item loaded:", item_name)
            count += 1
    print(f"Success: help namespace {namespace} loaded successfully with {count} items")


def dump_help(namespace: str, path_to_help: str, crlf) -> None:
    """
    Save an entire help namespace to the distribution source.
    Items with alias names must be copied only once.
    """
    logger.info("Dump help started")
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
        alias_names = get_item(str(file_.fullname), meta_file, data_file, CURRENT, "\r\n" if crlf else "\n")
        if alias_names:
            # no harm in adding current name to no_alias_dups
            no_alias_dups += alias_names
        print("Item dumped::", file_.relname)
        count += 1
    print(f"Success: help namespace {namespace} saved with {count} items")


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("item-get", help="Get an item revision from the wiki")
@click.option("--name", "-n", type=str, required=True, help="Name of the item to get.")
@click.option(
    "--meta", "-m", "--meta_file", type=str, required=True, help="Filename of the file to create for the metadata."
)
@click.option(
    "--data", "-d", "--data_file", type=str, required=True, help="Filename of the file to create for the data."
)
@click.option(
    "--revid",
    "-r",
    type=str,
    required=False,
    default=CURRENT,
    help="Revision ID of the revision to get (default: current rev).",
)
@click.option("--crlf/--no-crlf", help="Use Windows line endings in output files")
def GetItem(name, meta, data, revid, crlf) -> None:
    logger.info("Get item started")
    get_item(name, meta, data, revid, "\r\n" if crlf else "\n")
    logger.info("Get item finished")


@cli.command("item-put", help="Put an item revision into the wiki")
@click.option(
    "--meta", "-m", "--meta-file", type=str, required=True, help="Filename of the file to read for the metadata."
)
@click.option("--data", "-d", "--data-file", type=str, required=True, help="Filename of the file to read for the data.")
@click.option(
    "--overwrite", "-o", is_flag=True, default=False, help="If given, overwrite existing revisions, if requested."
)
def PutItem(meta, data, overwrite: bool) -> None:
    logger.info("Put item started")
    put_item(meta, data, overwrite)
    logger.info("Put item finished")


@cli.command("load-help", help="Load a directory of help .data and .meta file pairs into a wiki namespace")
@click.option("--namespace", "-n", type=str, required=True, help="Namespace to be loaded: help-common, help-en, etc.")
@click.option("--path_to_help", "--path", "-p", type=str, help="Override source directory, default is src/moin/help")
def LoadHelp(namespace, path_to_help) -> None:
    load_help(namespace, path_to_help)


@cli.command("dump-help", help="Dump a namespace of user help items to .data and .meta file pairs")
@click.option("--namespace", "-n", type=str, required=True, help="Namespace to be dumped: help-common, help-en, etc.")
@click.option("--path_to_help", "--path", "-p", type=str, help="Override output directory, default is src/moin/help")
@click.option("--crlf/--no-crlf", help="Use Windows line endings in output files")
def DumpHelp(namespace, path_to_help, crlf) -> None:
    dump_help(namespace, path_to_help, crlf)


@cli.command("welcome", help="Load initial welcome page into an empty wiki")
def LoadWelcome() -> None:
    load_welcome()
