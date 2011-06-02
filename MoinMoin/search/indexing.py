# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
 MoinMoin - MoinMoin.indexing Indexing Mechanism
"""


import os.path

from whoosh.fields import Schema, TEXT, ID, IDLIST, NUMERIC, DATETIME
from whoosh.analysis import entoken
from whoosh.index import open_dir, create_in

from MoinMoin.search.analyzers import *
from MoinMoin import log
logging = log.getLogger(__name__)

'''
for text items, it will be duplication. For "binary" items, it will only store
what the filter code outputs (e.g. if it is a PDF, it will only store what
pdftotext outputs as text, if it is a mp3, it will only store title/author/genre 
[not the whole mp3, of course])
'''


class WhooshIndex(object):

    items_schema=Schema(item_name=TEXT(stored=True, analyzer=item_name_analyzer),
                        uuid=ID(unique=True, stored=True),
                        rev_no=NUMERIC(stored=True),
                        datetime=DATETIME(stored=True),
                        content=TEXT(stored=True),
                        mimetype=TEXT(stored=True, analyzer=MimeTokenizer),
                        tags=TEXT(analyzer=entoken, stored=True),
                        itemlinks=TEXT(analyzer=entoken, stored=True),
                        itemtransclusions=TEXT(analyzer=entoken, stored=True),
                        acl=TEXT(analyzer=AclTokenizer, stored=True),
                        language=ID(stored=True),
                        metadata=TEXT(stored=True),
                       )

    revisions_schema = Schema(item_name=TEXT(stored=True, analyzer=item_name_analyzer),
                              uuid=ID(stored=True),
                              rev_no=NUMERIC(stored=True),
                              datetime=DATETIME(stored=True),
                              content=TEXT(stored=True),
                              mimetype=TEXT(stored=True,analyzer=MimeTokenizer),
                              tags=TEXT(analyzer=entoken, stored=True),
                              language=ID(stored=True),
                              metadata=TEXT(stored=True),
                             )
    index_path = "MoinMoin/search/index/"
    items = "items"
    revisions = "revisions"

    def __init__(self):
        if not os.path.exists(self.index_path): # checking what MoinMoin/search/index exists
            try:
                from os import mkdir
                schema = ""
                mkdir(self.index_path) # create if it doesn't exist
                # create index dirs for items and revisions schemas under MoinMoin/search/index
                for schema in [self.items, self.revisions]:
                    mkdir(self.index_path + schema)
                    create_in(self.index_path + schema, getattr(self, schema + "_schema"))
            except IOError:
                logging.error(u"Can not create '%s' index directory" % self.index_path + schema)
        try:
        # Try to open it
            schema = ""
            for schema in [self.items, self.revisions]:
                setattr(self, schema, open_dir(self.index_path + schema))
        except IOError:
            logging.error(u"Can not open '%s'. Manually remove '%s' and rebuild indexes" % (self.index_path + schema, self.index_path))

    def rebuild(self):
        pass

    def add(self):
        pass

    def remove(self):
        pass

