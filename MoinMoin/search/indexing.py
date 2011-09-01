# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Whoosh index schemas / index managment
"""

import os
import datetime

from flask import current_app as app

from whoosh.fields import Schema, TEXT, ID, IDLIST, NUMERIC, DATETIME, KEYWORD, BOOLEAN
from whoosh.index import open_dir, create_in, EmptyIndexError

from MoinMoin.config import MTIME, NAME, NAME_EXACT, REV_NO, WIKINAME, CONTENT
from MoinMoin.search.analyzers import *
from MoinMoin.error import FatalError

from MoinMoin import log
logging = log.getLogger(__name__)


def backend_to_index(backend_rev, rev_no, schema, content, wikiname=u''):
    """
    Convert fields from backend format to whoosh schema

    :param backend_rev: MoinMoin backend revision
    :param rev_no: Revision number
    :param schema_fields: list with whoosh schema fields
    :returns: document to put into whoosh index
    """

    doc = dict([(str(key), value)
                for key, value in backend_rev.items()
                if key in schema])
    doc[MTIME] = datetime.datetime.utcfromtimestamp(backend_rev[MTIME])
    doc[NAME_EXACT] = backend_rev[NAME]
    doc[REV_NO] = rev_no
    doc[WIKINAME] = wikiname
    doc[CONTENT] = content
    return doc


class WhooshIndex(object):
    """
    Managing whoosh indexes
    """

    # Index names, schemas
    _indexes = {'latest_revisions_index': 'latest_revisions_schema',
                'all_revisions_index': 'all_revisions_schema',
               }

    def __init__(self, index_dir=None, cfg=None, force_create=False):
        """
        Create and open indexes in index_dir

        :param force_create: Create empty index in index_dir even if index exists
        :param index_dir: Directory where whoosh indexes will be created, default None
        :param cfg: Application config (app.cfg), default None
        """
        self._cfg = cfg or app.cfg
        self._index_dir = index_dir or self._cfg.index_dir

        common_fields = dict(
            # wikiname so we can have a shared index in a wiki farm, always check this!
            # taken from app.cfg.interwikiname
            wikiname=ID(stored=True),
            # tokenized NAME from metadata - use this for manual searching from UI
            name=TEXT(stored=True, multitoken_query="and", analyzer=item_name_analyzer(), field_boost=2.0),
            # unmodified NAME from metadata - use this for precise lookup by the code.
            # also needed for wildcard search, so the original string as well as the query
            # (with the wildcard) is not cut into pieces.
            name_exact=ID(field_boost=3.0),
            # revision number, integer 0..n
            rev_no=NUMERIC(stored=True),
            # MTIME from revision metadata (converted to UTC datetime)
            mtime=DATETIME(stored=True),
            # tokenized CONTENTTYPE from metadata
            contenttype=TEXT(stored=True, multitoken_query="and", analyzer=MimeTokenizer()),
            # unmodified list of TAGS from metadata
            tags=ID(stored=True),
            # LANGUAGE from metadata
            language=ID(stored=True),
            # USERID from metadata
            userid=ID(stored=True),
            # ADDRESS from metadata
            address=ID(stored=True),
            # HOSTNAME from metadata
            hostname=ID(stored=True),
            # SIZE from metadata
            size=NUMERIC(stored=True),
            # ACTION from metadata
            action=ID(stored=True),
            # tokenized COMMENT from metadata
            comment=TEXT(stored=True, multitoken_query="and"),
            # data (content), converted to text/plain and tokenized
            content=TEXT(stored=True, multitoken_query="and"),
        )
        latest_revs_fields = dict(
            # UUID from metadata - as there is only latest rev of same item here, it is unique
            uuid=ID(unique=True, stored=True),
            # unmodified list of ITEMLINKS from metadata
            itemlinks=ID(stored=True),
            # unmodified list of ITEMTRANSCLUSIONS from metadata
            itemtransclusions=ID(stored=True),
            # tokenized ACL from metadata
            acl=TEXT(analyzer=AclTokenizer(self._cfg), multitoken_query="and", stored=True),
            **common_fields
        )

        all_revs_fields = dict(
            # UUID from metadata
            uuid=ID(stored=True),
            **common_fields
        )

        self.latest_revisions_schema = Schema(**latest_revs_fields)
        self.all_revisions_schema = Schema(**all_revs_fields)

        # Define dynamic fields
        dynamic_fields = [("*_id", ID(stored=True)),
                          ("*_text", TEXT(stored=True)),
                          ("*_keyword", KEYWORD(stored=True)),
                          ("*_numeric", NUMERIC(stored=True)),
                          ("*_datetime", DATETIME(stored=True)),
                          ("*_boolean", BOOLEAN(stored=True)),
                         ]

        # Adding dynamic fields to schemas
        for glob, field_type in dynamic_fields:
            self.latest_revisions_schema.add(glob, field_type, glob=True)
            self.all_revisions_schema.add(glob, field_type, glob=True)

        for index_name, index_schema in self._indexes.items():
            self.open_index(index_name, index_schema, create=True, force_create=force_create,
                            index_dir=self._index_dir
                           )

    def open_index(self, indexname, schema, create=False, force_create=False, index_dir=None):
        """
        Open index <indexname> in <index_dir>. if opening fails and <create>
        is True, try creating the index and retry opening it afterwards.
        return index object.


        :param indexname: Name of created index
        :param schema: which schema applies
        :param create: create index if index doesn't exist
        :param force_create: force create new empty index in index_dir
        :param index_dir: Directory where whoosh indexes will be created
        """
        index_dir = index_dir or self._cfg.index_dir
        if force_create:
            self.create_index(index_dir, indexname, schema)
        try:
            index = open_dir(index_dir, indexname=indexname)
            setattr(self, indexname, index)
        except (IOError, OSError, EmptyIndexError) as err:
            if create:
                self.create_index(index_dir, indexname, schema)
                try:
                    index = open_dir(index_dir, indexname=indexname)
                    setattr(self, indexname, index)
                except:
                    # if we get here, it failed without recovery
                    raise FatalError("can't open whoosh index")
            else:
                raise FatalError("can't open whoosh index")

    def create_index(self, index_dir, indexname, schema):
        """
        Create <indexname> in <index_dir>

        :param index_dir: Directory where whoosh indexes will be created
        :param indexname: Name of created index
        :param schema: which schema applies
        """
        try:
            os.mkdir(index_dir)
        except:
            # ignore exception, we'll get another exception below
            # in case there are problems with the index_dir
            pass
        try:
            create_in(index_dir, getattr(self, schema), indexname=indexname)
        except (IOError, OSError) as err:
            logging.error(u"%s [while trying to create index '%s' in '%s']" % (str(err), indexname, index_dir))

    def remove_index(self):
        """
        Create empty index in index_dir and removing old
        """
        for index_name, index_schema in self._indexes.items():
            self.create_index(indexname=index_name, schema=index_schema, index_dir=self._index_dir)
