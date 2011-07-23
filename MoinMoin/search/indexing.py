# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.indexing Indexing Mechanism
"""

import os
from flask import current_app as app

from whoosh.fields import Schema, TEXT, ID, IDLIST, NUMERIC, DATETIME
from whoosh.analysis import entoken
from whoosh.index import open_dir, create_in, EmptyIndexError

from MoinMoin.search.analyzers import *
from MoinMoin.error import FatalError
from MoinMoin import log
logging = log.getLogger(__name__)


class WhooshIndex(object):
    """
    Creating\opening whoosh indexes using "latest_revisions_schema" and
    "all_revisions_schema"
    """

    latest_revisions_schema = Schema(wikiname=ID(stored=True),
                                     name=TEXT(stored=True, analyzer=item_name_analyzer()),
                                     name_exact=ID,
                                     uuid=ID(unique=True, stored=True),
                                     rev_no=NUMERIC(stored=True),
                                     mtime=DATETIME(stored=True),
                                     content=TEXT(stored=True),
                                     contenttype=TEXT(stored=True, analyzer=MimeTokenizer()),
                                     tags=ID(stored=True),
                                     itemlinks=ID(stored=True),
                                     itemtransclusions=ID(stored=True),
                                     acl=TEXT(analyzer=AclTokenizer(), stored=True),
                                     language=ID(stored=True),
                                     userid=ID(stored=True),
                                     address=ID(stored=True),
                                     hostname=ID(stored=True),
                                    )

    all_revisions_schema = Schema(wikiname=ID(stored=True),
                                  name=TEXT(stored=True, analyzer=item_name_analyzer()),
                                  name_exact=ID,
                                  uuid=ID(stored=True),
                                  rev_no=NUMERIC(stored=True),
                                  mtime=DATETIME(stored=True),
                                  content=TEXT(stored=True),
                                  contenttype=TEXT(stored=True, analyzer=MimeTokenizer()),
                                  tags=TEXT(stored=True),
                                  language=ID(stored=True),
                                  userid=ID(stored=True),
                                  address=ID(stored=True),
                                  hostname=ID(stored=True),
                                 )
    # Index names, schemas
    indexes = {'latest_revisions_index': 'latest_revisions_schema',
               'all_revisions_index': 'all_revisions_schema',
              }

    def __init__(self, index_dir=None):
        """
        Create and open indexes in index_dir

        :param index_dir: Directory where whoosh indexes will be created, default None
        """

        index_dir = index_dir or app.cfg.index_dir
        for index_name, index_schema in self.indexes.items():
            self.open_index(index_dir, index_name, index_schema, create=True)

    def open_index(self, index_dir, indexname, schema, create=False):
        """
        open index <indexname> in <index_dir>. if opening fails and <create>
            is True, try creating the index and retry opening it afterwards.
            return index object.

        :param index_dir: Directory where whoosh indexes will be created
        :param indexname: Name of created index
        :param schema: which schema applies
        """

        try: # open indexes
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
