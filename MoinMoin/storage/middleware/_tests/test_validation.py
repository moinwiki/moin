# Copyright: 2011,2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - validation tests
"""


from __future__ import absolute_import, division

import pytest

from MoinMoin.storage.middleware.validation import ContentMetaSchema, UserMetaSchema

from MoinMoin.constants import keys
from MoinMoin.config import CONTENTTYPE_USER

from MoinMoin.util.crypto import make_uuid


class TestValidation(object):
    def test_content(self):
        class REV(dict):
            """ fake rev """

        rev = REV()
        rev[keys.ITEMID] = make_uuid()
        rev[keys.REVID] = make_uuid()
        rev[keys.ACL] = u"All:read"

        meta = {
            keys.REVID: make_uuid(),
            keys.PARENTID: make_uuid(),
            keys.NAME: u"a",
            keys.ACL: u"All:read",
            keys.TAGS: [u"foo", u"bar"],
        }

        state = {'trusted': False, # True for loading a serialized representation or other trusted sources
                 keys.NAME: u'somename', # name we decoded from URL path
                 keys.ACTION: u'SAVE',
                 keys.HOSTNAME: u'localhost',
                 keys.ADDRESS: u'127.0.0.1',
                 keys.USERID: make_uuid(),
                 keys.HASH_ALGORITHM: u'b9064b9a5efd8c6cef2d38a8169a0e1cbfdb41ba',
                 keys.SIZE: 0,
                 keys.WIKINAME: u'ThisWiki',
                 'rev_parent': rev,
                 'acl_parent': u"All:read",
                 'contenttype_current': u'text/x.moin.wiki;charset=utf-8',
                 'contenttype_guessed': u'text/plain;charset=utf-8',
                }

        m = ContentMetaSchema(meta)
        valid = m.validate(state)
        assert m[keys.CONTENTTYPE].value == u'text/x.moin.wiki;charset=utf-8'
        if not valid:
            for e in m.children:
                print e.valid, e
            print m.valid, m
        assert valid

    def test_user(self):
        meta = {
            keys.ITEMID: make_uuid(),
            keys.REVID: make_uuid(),
            keys.NAME: u"user name",
            keys.EMAIL: u"foo@example.org",
        }

        state = {'trusted': False, # True for loading a serialized representation or other trusted sources
                 keys.NAME: u'somename', # name we decoded from URL path
                 keys.ACTION: u'SAVE',
                 keys.HOSTNAME: u'localhost',
                 keys.ADDRESS: u'127.0.0.1',
                 keys.WIKINAME: u'ThisWiki',
                }

        m = UserMetaSchema(meta)
        valid = m.validate(state)
        assert m[keys.CONTENTTYPE].value == CONTENTTYPE_USER
        if not valid:
            for e in m.children:
                print e.valid, e
            print m.valid, m
        assert valid
