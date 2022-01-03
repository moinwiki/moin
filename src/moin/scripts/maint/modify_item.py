# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - get an item revision from the wiki, put it back into the wiki.
"""

import json
import io

from flask import current_app as app
from flask_script import Command, Option
from flask import g as flaskg

from moin.constants.keys import CURRENT, ITEMID, REVID, DATAID, SIZE, HASH_ALGORITHM
from moin.utils.interwiki import split_fqname


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
        query = {ITEMID: meta[ITEMID]}
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
