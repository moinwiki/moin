# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
 MoinMoin - MoinMoin.indexing Indexing Mechanism
"""


from whoosh.fields import TEXT, ID, IDLIST, NUMERIC, DATETIME
from whoosh.analysis import entoken

from MoinMoin.search.analyzers import *

'''
for text items, it will be duplication. For "binary" items, it will only store
what the filter code outputs (e.g. if it is a PDF, it will only store what
pdftotext outputs as text, if it is a mp3, it will only store title/author/genre 
[not the whole mp3, of course])
'''


class WhooshIndex(object):

    item_schema=Schema(item_name=TEXT(stored=True, analyzer=item_name_analyzer),
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

    def rebuild():
        pass

    def add():
        pass

    def remove():
        pass

