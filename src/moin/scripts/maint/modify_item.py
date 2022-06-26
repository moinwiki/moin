# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2022 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - get an item revision from the wiki, put it back into the wiki.
"""

import json
import io
import os

from flask import current_app as app
from flask_script import Command, Option
from flask import g as flaskg

from moin.constants.keys import CURRENT, ITEMID, REVID, DATAID, SIZE, HASH_ALGORITHM, NAMESPACE
from moin.utils.interwiki import split_fqname
from moin.items import Item
from moin.app import before_wiki


class GetItem(Command):
    description = 'Get an item revision from the wiki.'
    option_list = (
        Option('--name', '-n', dest='name', type=str, required=True,
               help='Name of the item to get.'),
        Option('--revid', '-r', dest='revid', type=str, required=False, default=CURRENT,
               help='Revision ID of the revision to get (default: current rev).'),
        Option('--meta', '-m', dest='meta_file', type=str, required=True,
               help='Filename of file to create for the metadata.'),
        Option('--data', '-d', dest='data_file', type=str, required=True,
               help='Filename of file to create for the data.'),
    )

    def run(self, name, meta_file, data_file, revid):
        fqname = split_fqname(name)
        item = app.storage.get_item(**fqname.query)
        rev = item[revid]
        meta = json.dumps(dict(rev.meta), sort_keys=True, indent=2, ensure_ascii=False)
        with open(meta_file, 'w', encoding='utf-8') as mf:
            mf.write(meta)
        if 'charset' in rev.meta['contenttype']:
            # input data will have \r\n line endings, output will have platform dependent line endings
            charset = rev.meta['contenttype'].split('charset=')[1]
            data = rev.data.read().decode(charset)
            lines = data.splitlines()
            lines = '\n'.join(lines)
            with open(data_file, 'w', encoding=charset) as df:
                df.write(lines)
            return

        data = rev.data.read()
        with open(data_file, 'wb') as df:
            df.write(data)


class PutItem(Command):
    description = 'Put an item revision into the wiki.'
    option_list = (
        Option('--meta', '-m', dest='meta_file', type=str, required=True,
               help='Filename of file to read as metadata.'),
        Option('--data', '-d', dest='data_file', type=str, required=True,
               help='Filename of file to read as data.'),
        Option('--overwrite', '-o', action='store_true', dest='overwrite', default=False,
               help='If given, overwrite existing revisions, if requested.'),
    )

    def run(self, meta_file, data_file, overwrite):
        flaskg.add_lineno_attr = False
        with open(meta_file, 'rb') as mf:
            meta = mf.read()
        meta = meta.decode('utf-8')
        meta = json.loads(meta)
        to_kill = [SIZE, HASH_ALGORITHM,  # gets re-computed automatically
                   DATAID,
                   ]
        for key in to_kill:
            meta.pop(key, None)
        if not overwrite:
            # if we remove the REVID, it will create a new one and store under the new one
            meta.pop(REVID, None)
        query = {ITEMID: meta[ITEMID], NAMESPACE: meta[NAMESPACE]}
        item = app.storage.get_item(**query)

        # we want \r\n line endings in data out because \r\n is required in form textareas
        if 'charset' in meta['contenttype']:
            charset = meta['contenttype'].split('charset=')[1]
            with open(data_file, 'rb') as df:
                data = df.read().decode(charset)
            if '\r\n' not in data and '\n' in data:
                data = data.replace('\n', '\r\n')
                data = data.encode(charset)
                buffer = io.BytesIO()
                buffer.write(data)
                buffer.seek(0)
                item.store_revision(meta, buffer, overwrite=overwrite)
                buffer.close()
                return

        with open(data_file, 'rb') as df:
            item.store_revision(meta, df, overwrite=overwrite)


class LoadHelp(Command):
    """
    Load an entire help namespace from distribution source.
    """
    description = 'Load a directory of help .data and .meta file pairs into a wiki namespace'
    option_list = (
        Option('--namespace', '-n', dest='namespace', type=str, required=True,
               help='Namespace to be loaded: common, en, etc.'),
        Option('--path', '-p', dest='path_to_help', type=str, default='../../help/',
               help='Override default input directory'),
    )

    def run(self, namespace, path_to_help):
        abspath_to_here = os.path.dirname(os.path.abspath(__file__))
        path_to_items = os.path.normpath(os.path.join(abspath_to_here, path_to_help, namespace))
        if not os.path.isdir(path_to_items):
            print('Abort: the {0} directory does not exist'.format(path_to_items))
            return
        file_list = os.listdir(path_to_items)
        if not len(file_list):
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
                PutItem.run(self, meta_file, data_file, True)
                print('Item loaded:', item_name)
                count += 1
        print('Success: help namespace {0} loaded successfully with {1} items'.format(namespace, count))


class DumpHelp(Command):
    """
    Save an entire help namespace to the distribution source.
    """
    description = 'Dump a namespace of user help items to .data and .meta file pairs'
    option_list = (
        Option('--namespace', '-n', dest='namespace', type=str, required=True,
               help='Namespace to be dumped: common, en, etc.'),
        Option('--path', '-p', dest='path_to_help', type=str, default='../../help/',
               help='Override default output directory'),
    )

    def run(self, namespace, path_to_help):
        before_wiki()
        abspath_to_here = os.path.dirname(os.path.abspath(__file__))
        item_name = 'help-' + namespace
        # item_name is a namespace, we create a dummy item so we can get a list of files
        item = Item.create(item_name)
        dirs, files = item.get_index()
        count = 0
        no_alias_dups = []
        for file_ in files:
            if file_.relname in no_alias_dups:
                continue
            no_alias_dups.append(file_.relname)
            # convert / characters to avoid invalid paths
            esc_name = file_.relname.replace('/', '%2f')
            meta_file = os.path.abspath(os.path.join(abspath_to_here, path_to_help, namespace, esc_name + '.meta'))
            data_file = os.path.abspath(os.path.join(abspath_to_here, path_to_help, namespace, esc_name + '.data'))
            GetItem.run(self, str(file_.fullname), meta_file, data_file, CURRENT)
            print('Item dumped::', file_.relname)
            count += 1
        print('Success: help namespace {0} saved with {1} items'.format(namespace, count))
