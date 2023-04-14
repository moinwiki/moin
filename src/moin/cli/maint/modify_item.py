# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:RogerHaase
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin CLI - get an item revision from the wiki, put it back into the wiki.
"""

import json
import io
import os

import click
from flask import current_app as app
from flask import g as flaskg
from flask.cli import FlaskGroup

from moin.app import create_app, before_wiki
from moin.constants.keys import CURRENT, ITEMID, REVID, DATAID, NAMESPACE, WIKINAME
from moin.utils.interwiki import split_fqname
from moin.items import Item

from moin import log, help as moin_help

logging = log.getLogger(__name__)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command('item-get', help='Get an item revision from the wiki')
@click.option('--name', '-n', type=str, required=True, help='Name of the item to get.')
@click.option('--meta', '-m', '--meta_file', type=str, required=True,
              help='Filename of file to create for the metadata.')
@click.option('--data', '-d', '--data_file', type=str, required=True,
              help='Filename of file to create for the data.')
@click.option('--revid', '-r', type=str, required=False, default=CURRENT,
              help='Revision ID of the revision to get (default: current rev).')
@click.option('--crlf/--no-crlf', help='use windows line endings in output files')
def cli_GetItem(name, meta, data, revid, crlf):
    logging.info("Get item started")
    GetItem(name, meta, data, revid, '\r\n' if crlf else '\n')
    logging.info("Get item finished")


def GetItem(name, meta_file, data_file, revid, newline='\n'):
    """
    Get an item revision from the wiki and save in files
    """
    fqname = split_fqname(name)
    item = app.storage.get_item(**fqname.query)
    rev = item[revid]
    meta = json.dumps(dict(rev.meta), sort_keys=True, indent=2, ensure_ascii=False)
    with open(meta_file, 'w', encoding='utf-8', newline=newline) as mf:
        mf.write(meta + '\n')
    if 'charset' in rev.meta['contenttype']:
        # input data will have \r\n line endings, output will have specified endings
        # those running on windows with git autocrlf=true will want --crlf
        # those running on linux or with autocrlf=input will want --no-crlf
        charset = rev.meta['contenttype'].split('charset=')[1]
        data = rev.data.read().decode(charset)
        lines = data.splitlines()
        # add trailing line ending which may have been removed by splitlines,
        # or add extra trailing line ending which will be removed in _PutItem if file is imported
        lines = '\n'.join(lines) + '\n'
        with open(data_file, 'w', encoding=charset, newline=newline) as df:
            df.write(lines)
        return

    data = rev.data.read()
    with open(data_file, 'wb') as df:
        df.write(data)
    logging.info("Get item finished")


@cli.command('item-put', help='Put an item revision into the wiki')
@click.option('--meta', '-m', '--meta-file', type=str, required=True,
              help='Filename of file to read as metadata.')
@click.option('--data', '-d', '--data-file', type=str, required=True,
              help='Filename of file to read as data.')
@click.option('--overwrite', '-o', is_flag=True, default=False,
              help='If given, overwrite existing revisions, if requested.')
def cli_PutItem(meta, data, overwrite):
    logging.info("Put item started")
    PutItem(meta, data, overwrite)
    logging.info("Put item finished")


def PutItem(meta_file, data_file, overwrite):
    """
    Put an item revision from file into the wiki
    """
    flaskg.add_lineno_attr = False
    with open(meta_file, 'rb') as mf:
        meta = mf.read()
    meta = meta.decode('utf-8')
    meta = json.loads(meta)
    to_kill = [WIKINAME, ]  # use target wiki name
    for key in to_kill:
        meta.pop(key, None)
    if not overwrite:
        # if we remove the REVID, it will create a new one and store under the new one
        meta.pop(REVID, None)
        meta.pop(DATAID, None)
    query = {ITEMID: meta[ITEMID], NAMESPACE: meta[NAMESPACE]}
    logging.debug("query: {}".format(str(query)))
    item = app.storage.get_item(**query)

    # we want \r\n line endings in data out because \r\n is required in form textareas
    if 'charset' in meta['contenttype']:
        charset = meta['contenttype'].split('charset=')[1]
        with open(data_file, 'rb') as df:
            data = df.read().decode(charset)
        if '\r\n' not in data and '\n' in data:
            data = data.replace('\n', '\r\n')
        data = data.encode(charset)
        if 0 < len(data) - meta['size'] <= 2:
            data = data[0:meta['size']]  # potentially truncate trailing newline added by _GetItem
        buffer = io.BytesIO()
        buffer.write(data)
        buffer.seek(0)
        item.store_revision(meta, buffer, overwrite=overwrite)
        buffer.close()
        return

    with open(data_file, 'rb') as df:
        item.store_revision(meta, df, overwrite=overwrite)


@cli.command('load-help', help='Load a directory of help .data and .meta file pairs into a wiki namespace')
@click.option('--namespace', '-n', type=str, required=True,
              help='Namespace to be loaded: common, en, etc.')
@click.option('--path_to_help', '--path', '-p', type=str, default='../../help/',
              help='Override default input directory')
def cli_LoadHelp(namespace, path_to_help):
    return LoadHelp(namespace, path_to_help)


def LoadHelp(namespace, path_to_help):
    """
    Load an entire help namespace from distribution source.
    """
    logging.info("Load help started")
    abspath_to_here = os.path.dirname(os.path.abspath(__file__))
    path_to_items = os.path.normpath(os.path.join(abspath_to_here, path_to_help, namespace))
    if not os.path.isdir(path_to_items):
        print('Abort: the {0} directory does not exist'.format(path_to_items))
        return
    file_list = os.listdir(path_to_items)
    if len(file_list) == 0:
        print('Abort: the {0} directory is empty'.format(path_to_items))
        return
    count = 0
    for f in file_list:
        if f.endswith('.meta'):
            # filenames must have / characters replaced with %2f, item will be saved with name(s) in metadata
            item_name = f[:-5].replace('%2f', '/')
            data_file = f.replace('.meta', '.data')
            meta_file = os.path.join(path_to_items, f)
            data_file = os.path.join(path_to_items, data_file)
            PutItem(meta_file, data_file, "true")
            print('Item loaded:', item_name)
            count += 1
    print('Success: help namespace {0} loaded successfully with {1} items'.format(namespace, count))


@cli.command('dump-help', help='Dump a namespace of user help items to .data and .meta file pairs')
@click.option('--namespace', '-n', type=str, required=True,
              help='Namespace to be dumped: common, en, etc.')
@click.option('--path_to_help', '--path', '-p', type=str,
              help='Override default output directory'
                   '(default works in source directory - ../../help/ relative to src/moin/cli/maint)')
@click.option('--crlf/--no-crlf', help='use windows line endings in output files')
def DumpHelp(namespace, path_to_help, crlf):
    """
    Save an entire help namespace to the distribution source.
    """
    logging.info("Dump help started")
    before_wiki()
    if path_to_help is None:
        abspath_to_here = os.path.dirname(os.path.abspath(__file__))
        path_to_help = os.path.abspath(os.path.join(abspath_to_here, '../../help/'))
    item_name = 'help-' + namespace
    # item_name is a namespace, we create a dummy item so we can get a list of files
    item = Item.create(item_name)
    _, files = item.get_index()
    count = 0
    no_alias_dups = []
    for file_ in files:
        if file_.relname in no_alias_dups:
            continue
        no_alias_dups.append(file_.relname)
        # convert / characters to avoid invalid paths
        esc_name = file_.relname.replace('/', '%2f')
        meta_file = os.path.join(path_to_help, namespace, esc_name + '.meta')
        data_file = os.path.join(path_to_help, namespace, esc_name + '.data')
        GetItem(str(file_.fullname), meta_file, data_file, CURRENT, '\r\n' if crlf else '\n')
        print('Item dumped::', file_.relname)
        count += 1
    print('Success: help namespace {0} saved with {1} items'.format(namespace, count))


@cli.command('welcome', help='Load initial welcome page into an empty wiki')
def cli_LoadWelcome():
    return LoadWelcome()


def LoadWelcome():
    """
    Load a welcome page as initial home from distribution source.
    """
    logging.info("Load welcome page started")
    help_path = os.path.dirname(moin_help.__file__)
    path_to_items = os.path.normpath(os.path.join(help_path, 'welcome'))
    meta_file = os.path.join(path_to_items, 'Home.meta')
    data_file = os.path.join(path_to_items, 'Home.data')
    PutItem(meta_file, data_file, "true")
    logging.info("Load welcome finished")
