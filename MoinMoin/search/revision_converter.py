# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Backend revision to whoosh revision converter
"""


import datetime

from MoinMoin.config import MTIME, NAME

def backend_to_index(backend_rev, rev_no, schema_fields, content, wikiname=u''):
    """
    Convert fields from backend format to whoosh schema

    :param backend_rev: MoinMoin backend revision
    :param rev_no: Revision number
    :param schema_fields: list with whoosh schema fields
    :returns: document to put into whoosh index
    """

    doc = dict([(str(key), value)
                for key, value in backend_rev.items()
                if key in schema_fields])
    doc[MTIME] = datetime.datetime.fromtimestamp(backend_rev[MTIME])
    doc["name_exact"] = backend_rev[NAME]
    doc["rev_no"] = rev_no
    doc["wikiname"] = wikiname
    doc["content"] = content
    return doc

