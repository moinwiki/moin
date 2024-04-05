# Copyright: 2011,2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - validation tests
"""

from moin.storage.middleware.validation import ContentMetaSchema, UserMetaSchema

from moin.constants import keys
from moin.constants.contenttypes import CONTENTTYPE_USER

from moin.utils.crypto import make_uuid

from moin.utils.interwiki import CompositeName


class TestValidation:
    def test_content(self):
        class REV(dict):
            """fake rev"""

        rev = REV()
        rev[keys.ITEMID] = make_uuid()
        rev[keys.REVID] = make_uuid()
        rev[keys.ACL] = "All:read"

        meta = {
            keys.REVID: make_uuid(),
            keys.PARENTID: make_uuid(),
            keys.NAME: ["a"],
            keys.NAMESPACE: "",
            keys.ACL: "All:read",
            keys.TAGS: ["foo", "bar"],
        }

        state = {
            "trusted": False,  # True for loading a serialized representation or other trusted sources
            keys.NAME: "somename",  # name we decoded from URL path
            keys.ACTION: keys.ACTION_SAVE,
            keys.HOSTNAME: "localhost",
            keys.ADDRESS: "127.0.0.1",
            keys.USERID: make_uuid(),
            keys.HASH_ALGORITHM: "b9064b9a5efd8c6cef2d38a8169a0e1cbfdb41ba",
            keys.SIZE: 0,
            keys.WIKINAME: "ThisWiki",
            keys.NAMESPACE: "",
            "rev_parent": rev,
            "acl_parent": "All:read",
            "contenttype_current": "text/x.moin.wiki;charset=utf-8",
            "contenttype_guessed": "text/plain;charset=utf-8",
            keys.FQNAME: CompositeName("", "", "somename"),
        }

        m = ContentMetaSchema(meta)
        valid = m.validate(state)
        assert m[keys.CONTENTTYPE].value == "text/x.moin.wiki;charset=utf-8"
        if not valid:
            for e in m.children:
                print(e.valid, e)
            print(m.valid, m)
        assert valid

    def test_user(self):
        meta = {
            keys.ITEMID: make_uuid(),
            keys.REVID: make_uuid(),
            keys.NAME: ["user name"],
            keys.NAMESPACE: "userprofiles",
            keys.EMAIL: "foo@example.org",
            keys.SUBSCRIPTIONS: [
                f"{keys.ITEMID}:{make_uuid()}",
                f"{keys.NAME}::foo",
                f"{keys.TAGS}::bar",
                f"{keys.NAMERE}::",
                f"{keys.NAMEPREFIX}:userprofiles:a",
            ],
        }

        invalid_meta = {keys.SUBSCRIPTIONS: ["", "unknown_tag:123", f"{keys.ITEMID}:123", f"{keys.NAME}:foo"]}

        state = {
            "trusted": False,  # True for loading a serialized representation or other trusted sources
            keys.NAME: "somename",  # name we decoded from URL path
            keys.ACTION: keys.ACTION_SAVE,
            keys.HOSTNAME: "localhost",
            keys.ADDRESS: "127.0.0.1",
            keys.WIKINAME: "ThisWiki",
            keys.NAMESPACE: "",
            keys.FQNAME: CompositeName("", "", "somename"),
        }

        m = UserMetaSchema(meta)
        valid = m.validate(state)
        assert m[keys.CONTENTTYPE].value == CONTENTTYPE_USER
        if not valid:
            for e in m.children:
                print(e.valid, e)
            print(m.valid, m)
        assert valid

        m = UserMetaSchema(invalid_meta)
        valid = m.validate(state)
        assert not valid
        for e in m.children:
            if e.name in (keys.SUBSCRIPTIONS,):
                for value in e:
                    assert not value.valid
