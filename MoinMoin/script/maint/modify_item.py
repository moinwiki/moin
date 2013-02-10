# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - get an item revision from the wiki, put it back into the wiki.
"""

import shutil
import json

from flask import current_app as app
from flask import g as flaskg
from flask.ext.script import Command, Option

from MoinMoin.constants.keys import CURRENT, ITEMID, REVID, DATAID, SIZE, HASH_ALGORITHM


class GetItem(Command):
    description = 'Get an item revision from the wiki.'
    option_list = (
        Option('--name', '-n', dest='name', type=unicode, required=True,
            help='Name of the item to get.'),
        Option('--revid', '-r', dest='revid', type=unicode, required=False, default=CURRENT,
            help='Revision ID of the revision to get (default: current rev).'),
        Option('--meta', '-m', dest='meta_file', type=unicode, required=True,
            help='Filename of file to create for the metadata.'),
        Option('--data', '-d', dest='data_file', type=unicode, required=True,
            help='Filename of file to create for the data.'),
    )

    def run(self, name, meta_file, data_file, revid):
        item = app.storage[name]
        rev = item[revid]
        meta = json.dumps(dict(rev.meta), sort_keys=True, indent=2, ensure_ascii=False)
        meta = meta.encode('utf-8')
        with open(meta_file, 'wb') as mf:
            mf.write(meta)
        with open(data_file, 'wb') as df:
            shutil.copyfileobj(rev.data, df)


class PutItem(Command):
    description = 'Put an item revision into the wiki.'
    option_list = (
        Option('--meta', '-m', dest='meta_file', type=unicode, required=True,
            help='Filename of file to read as metadata.'),
        Option('--data', '-d', dest='data_file', type=unicode, required=True,
            help='Filename of file to read as data.'),
        Option('--overwrite', '-o', action='store_true', dest='overwrite', default=False,
            help='If given, overwrite existing revisions, if requested.'),
    )

    def run(self, meta_file, data_file, overwrite):
        with open(meta_file, 'rb') as mf:
            meta = mf.read()
        meta = meta.decode('utf-8')
        meta = json.loads(meta)
        to_kill = [SIZE, HASH_ALGORITHM, # gets re-computed automatically
                   DATAID,
                  ]
        for key in to_kill:
            meta.pop(key, None)
        if not overwrite:
            # if we remove the REVID, it will create a new one and store under the new one
            meta.pop(REVID, None)
        query = {ITEMID: meta[ITEMID]}
        item = app.storage.get_item(**query)
        with open(data_file, 'rb') as df:
            item.store_revision(meta, df, overwrite=overwrite)
