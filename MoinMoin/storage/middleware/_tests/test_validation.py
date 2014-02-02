# Copyright: 2011,2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - validation tests
"""


from __future__ import absolute_import, division

from MoinMoin.storage.middleware.validation import ContentMetaSchema, UserMetaSchema

from MoinMoin.constants import keys
from MoinMoin.constants.contenttypes import CONTENTTYPE_USER

from MoinMoin.util.crypto import make_uuid

from MoinMoin.util.interwiki import CompositeName


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
            keys.NAME: [u"a", ],
            keys.NAMESPACE: u"",
            keys.ACL: u"All:read",
            keys.TAGS: [u"foo", u"bar"],
        }

        state = {'trusted': False,  # True for loading a serialized representation or other trusted sources
                 keys.NAME: u'somename',  # name we decoded from URL path
                 keys.ACTION: keys.ACTION_SAVE,
                 keys.HOSTNAME: u'localhost',
                 keys.ADDRESS: u'127.0.0.1',
                 keys.USERID: make_uuid(),
                 keys.HASH_ALGORITHM: u'b9064b9a5efd8c6cef2d38a8169a0e1cbfdb41ba',
                 keys.SIZE: 0,
                 keys.WIKINAME: u'ThisWiki',
                 keys.NAMESPACE: u'',
                 'rev_parent': rev,
                 'acl_parent': u"All:read",
                 'contenttype_current': u'text/x.moin.wiki;charset=utf-8',
                 'contenttype_guessed': u'text/plain;charset=utf-8',
                 keys.FQNAME: CompositeName(u'', u'', u'somename'),
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
            keys.NAME: [u"user name", ],
            keys.NAMESPACE: u"userprofiles",
            keys.EMAIL: u"foo@example.org",
            keys.SUBSCRIPTIONS: [u"{0}:{1}".format(keys.ITEMID, make_uuid()),
                                 u"{0}::foo".format(keys.NAME),
                                 u"{0}::bar".format(keys.TAGS),
                                 u"{0}::".format(keys.NAMERE),
                                 u"{0}:userprofiles:a".format(keys.NAMEPREFIX),
                                 ]
        }

        invalid_meta = {
            keys.SUBSCRIPTIONS: [u"", u"unknown_tag:123",
                                 u"{0}:123".format(keys.ITEMID),
                                 u"{0}:foo".format(keys.NAME),
                                 ]
        }

        state = {'trusted': False,  # True for loading a serialized representation or other trusted sources
                 keys.NAME: u'somename',  # name we decoded from URL path
                 keys.ACTION: keys.ACTION_SAVE,
                 keys.HOSTNAME: u'localhost',
                 keys.ADDRESS: u'127.0.0.1',
                 keys.WIKINAME: u'ThisWiki',
                 keys.NAMESPACE: u'',
                 keys.FQNAME: CompositeName(u'', u'', u'somename')
                }

        m = UserMetaSchema(meta)
        valid = m.validate(state)
        assert m[keys.CONTENTTYPE].value == CONTENTTYPE_USER
        if not valid:
            for e in m.children:
                print e.valid, e
            print m.valid, m
        assert valid

        m = UserMetaSchema(invalid_meta)
        valid = m.validate(state)
        assert not valid
        for e in m.children:
            if e.name in (keys.SUBSCRIPTIONS,):
                for value in e:
                    assert not value.valid
