# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 by MoinMoin:ReimarBauer
# Copyright: 2007,2009 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.security Tests
"""


import pytest

from flask import current_app as app

from moin.security import AccessControlList, ACLStringIterator

from moin.user import User
from moin.constants.keys import NAME, ACL
from moin.datastructures import ConfigGroups

from moin._tests import update_item, become_trusted, wikiconfig


def acliter(acl):
    """
    return a acl string iterator (using cfg.acl_rights_contents as valid acl rights)
    """
    return ACLStringIterator(app.cfg.acl_rights_contents, acl)


class TestACLStringIterator:

    def testEmpty(self):
        """security: empty acl string raise StopIteration"""
        acl_iter = acliter("")
        pytest.raises(StopIteration, acl_iter.__next__)

    def testWhiteSpace(self):
        """security: white space acl string raise StopIteration"""
        acl_iter = acliter("       ")
        pytest.raises(StopIteration, acl_iter.__next__)

    def testDefault(self):
        """security: default meta acl"""
        acl_iter = acliter("Default Default")
        for mod, entries, rights in acl_iter:
            assert entries == ["Default"]
            assert rights == []

    def testEmptyRights(self):
        """security: empty rights"""
        acl_iter = acliter("WikiName:")
        mod, entries, rights = next(acl_iter)
        assert entries == ["WikiName"]
        assert rights == []

    def testSingleWikiNameSingleRight(self):
        """security: single wiki name, single right"""
        acl_iter = acliter("WikiName:read")
        mod, entries, rights = next(acl_iter)
        assert entries == ["WikiName"]
        assert rights == ["read"]

    def testMultipleWikiNameAndRights(self):
        """security: multiple wiki names and rights"""
        acl_iter = acliter("UserOne,UserTwo:read,write")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne", "UserTwo"]
        assert rights == ["read", "write"]

    def testMultipleWikiNameAndRightsSpaces(self):
        """security: multiple names with spaces"""
        acl_iter = acliter("user one,user two:read")
        mod, entries, rights = next(acl_iter)
        assert entries == ["user one", "user two"]
        assert rights == ["read"]

    def testMultipleEntries(self):
        """security: multiple entries"""
        acl_iter = acliter("UserOne:read,write UserTwo:read All:")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne"]
        assert rights == ["read", "write"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserTwo"]
        assert rights == ["read"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["All"]
        assert rights == []

    def testNameWithSpaces(self):
        """security: single name with spaces"""
        acl_iter = acliter("user one:read")
        mod, entries, rights = next(acl_iter)
        assert entries == ["user one"]
        assert rights == ["read"]

    def testMultipleEntriesWithSpaces(self):
        """security: multiple entries with spaces"""
        acl_iter = acliter("user one:read,write user two:read")
        mod, entries, rights = next(acl_iter)
        assert entries == ["user one"]
        assert rights == ["read", "write"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["user two"]
        assert rights == ["read"]

    def testMixedNames(self):
        """security: mixed wiki names and names with spaces"""
        acl_iter = acliter("UserOne,user two:read,write user three,UserFour:read")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne", "user two"]
        assert rights == ["read", "write"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["user three", "UserFour"]
        assert rights == ["read"]

    def testModifier(self):
        """security: acl modifiers"""
        acl_iter = acliter("+UserOne:read -UserTwo:")
        mod, entries, rights = next(acl_iter)
        assert mod == "+"
        assert entries == ["UserOne"]
        assert rights == ["read"]
        mod, entries, rights = next(acl_iter)
        assert mod == "-"
        assert entries == ["UserTwo"]
        assert rights == []

    def testIgnoreInvalidACL(self):
        """security: ignore invalid acl

        The last part of this acl can not be parsed. If it ends with :
        then it will be parsed as one name with spaces.
        """
        acl_iter = acliter("UserOne:read user two is ignored")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne"]
        assert rights == ["read"]
        pytest.raises(StopIteration, acl_iter.__next__)

    def testEmptyNamesWithRight(self):
        """security: empty names with rights

        The documents does not talk about this case, may() should ignore
        the rights because there is no entry.
        """
        acl_iter = acliter("UserOne:read :read All:")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne"]
        assert rights == ["read"]
        mod, entries, rights = next(acl_iter)
        assert entries == []
        assert rights == ["read"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["All"]
        assert rights == []

    def testIgnoreInvalidRights(self):
        """security: ignore rights not in acl_rights_contents

        Note: this is also important for ACL regeneration (see also acl
              regeneration test for storage.backends.fs19).
        """
        acl_iter = acliter("UserOne:read,sing,write,drink,sleep")
        mod, entries, rights = next(acl_iter)
        assert rights == ["read", "write"]

        # we use strange usernames that include invalid rights as substrings
        acls = list(acliter("JimAdelete,JoeArevert:admin,read,delete,write,revert"))
        # now check that we have lost the invalid rights 'delete' and 'revert',
        # but the usernames should be still intact.
        assert acls == [("", ["JimAdelete", "JoeArevert"], ["admin", "read", "write"])]

    def testBadGuy(self):
        """security: bad guy may not allowed anything

        This test was failing on the apply acl rights test.
        """
        acl_iter = acliter("UserOne:read,write BadGuy: All:read")
        mod, entries, rights = next(acl_iter)
        mod, entries, rights = next(acl_iter)
        assert entries == ["BadGuy"]
        assert rights == []

    def testAllowExtraWhitespace(self):
        """security: allow extra white space between entries"""
        acl_iter = acliter("UserOne,user two:read,write   user three,UserFour:read  All:")
        mod, entries, rights = next(acl_iter)
        assert entries == ["UserOne", "user two"]
        assert rights == ["read", "write"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["user three", "UserFour"]
        assert rights == ["read"]
        mod, entries, rights = next(acl_iter)
        assert entries == ["All"]
        assert rights == []


class TestAcl:
    """security: testing access control list

    TO DO: test unknown user?
    """

    def testhasACL(self):
        acl = AccessControlList(valid=app.cfg.acl_rights_contents)
        assert not acl.has_acl()
        acl = AccessControlList(["All:read"], valid=app.cfg.acl_rights_contents)
        assert acl.has_acl()

    def testApplyACLByUser(self):
        """security: applying acl by user name"""
        # This acl string...
        acl_rights = [
            "-MinusGuy:read "
            "+MinusGuy:read "
            "+PlusGuy:read "
            "-PlusGuy:read "
            "Admin1,Admin2:read,write,admin  "
            "Admin3:read,write,admin  "
            "JoeDoe:read,write  "
            "name with spaces,another one:read,write  "
            "CamelCase,extended name:read,write  "
            "BadGuy:  "
            "All:read  "
        ]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        # Should apply these rights:
        users = (
            # user,                 rights
            # CamelCase names
            ("Admin1", ("read", "write", "admin")),
            ("Admin2", ("read", "write", "admin")),
            ("Admin3", ("read", "write", "admin")),
            ("JoeDoe", ("read", "write")),
            ("SomeGuy", ("read",)),
            # Extended names or mix of extended and CamelCase
            ("name with spaces", ("read", "write")),
            ("another one", ("read", "write")),
            ("CamelCase", ("read", "write")),
            ("extended name", ("read", "write")),
            # Blocking bad guys
            ("BadGuy", ()),
            # All other users - every one not mentioned in the acl lines
            ("All", ("read",)),
            ("Anonymous", ("read",)),
            # we check whether ACL processing stops for a user/right match
            # with ACL modifiers
            ("MinusGuy", ()),
            ("PlusGuy", ("read",)),
        )

        # Check rights
        for user, may in users:
            mayNot = [right for right in app.cfg.acl_rights_contents if right not in may]
            # User should have these rights...
            for right in may:
                assert acl.may(user, right)
            # But NOT these:
            for right in mayNot:
                assert not acl.may(user, right)


class TestGroupACL:

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            def groups(cfg):
                groups = {
                    "PGroup": frozenset(["Antony", "Beatrice"]),
                    "AGroup": frozenset(["All"]),
                    # note: the next line is a INTENDED misnomer, there is "All" in
                    # the group NAME, but not in the group members. This makes
                    # sure that a bug that erroneously checked "in groupname" (instead
                    # of "in groupmembers") does not reappear.
                    "AllGroup": frozenset([]),  # note: intended misnomer
                }
                return ConfigGroups(groups)

        return Config

    def testApplyACLByGroup(self):
        """security: applying acl by group name"""
        # This acl string...
        acl_rights = ["PGroup,AllGroup:read,write,admin " "AGroup:read "]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        # Should apply these rights:
        users = (
            # user, rights
            ("Antony", ("read", "write", "admin")),  # in PGroup
            ("Beatrice", ("read", "write", "admin")),  # in PGroup
            ("Charles", ("read",)),  # virtually in AGroup
        )

        # Check rights
        for user, may in users:
            mayNot = [right for right in app.cfg.acl_rights_contents if right not in may]
            # User should have these rights...
            for right in may:
                assert acl.may(user, right)
            # But NOT these:
            for right in mayNot:
                assert not acl.may(user, right)


class TestItemAcls:
    """security: real-life access control list on items testing"""

    mainitem_name = "AclTestMainItem"
    subitem1_name = "AclTestMainItem/SubItem1"
    subitem2_name = "AclTestMainItem/SubItem2"
    item_rwforall = "EveryoneMayReadWriteMe"
    subitem_4boss = "EveryoneMayReadWriteMe/OnlyTheBossMayWMe"
    items = [
        # itemname, acl, content
        (mainitem_name, "JoeDoe: JaneDoe:read,write", "Foo!"),
        # acl None means: "no acl given in item metadata" - this will trigger
        # usage of default acl (non-hierarchical) or usage of default acl and
        # inheritance (hierarchical):
        (subitem1_name, None, "FooFoo!"),
        # acl '' means: "empty acl (no rights for anyone) given" - this will
        # INHIBIT usage of default acl / inheritance (we DO HAVE an item acl,
        # it is just empty!):
        (subitem2_name, "", "BarBar!"),
        (item_rwforall, "All:read,write", "May be read from and written to by anyone"),
        (subitem_4boss, "JoeDoe:read,write", "Only JoeDoe (the boss) may write"),
    ]

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            default_acl = dict(
                hierarchic=False,
                before="WikiAdmin:admin,read,write,create,destroy",
                default="All:read,write",
                after="All:read",
            )
            acl_functions = "SuperUser:superuser"

        return Config

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        become_trusted(username="WikiAdmin")
        for item_name, item_acl, item_content in self.items:
            if item_acl is not None:
                update_item(item_name, {ACL: item_acl}, item_content)
            else:
                update_item(item_name, {}, item_content)

    def test_ItemACLs(self):
        """security: test item acls"""
        tests = [
            # itemname, username, expected_rights
            (self.mainitem_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.mainitem_name, "AnyUser", ["read"]),  # by after acl
            (self.mainitem_name, "JaneDoe", ["read", "write"]),  # by item acl
            (self.mainitem_name, "JoeDoe", []),  # by item acl
            (self.subitem1_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.subitem1_name, "AnyUser", ["read", "write"]),  # by default acl
            (self.subitem1_name, "JoeDoe", ["read", "write"]),  # by default acl
            (self.subitem1_name, "JaneDoe", ["read", "write"]),  # by default acl
            (self.subitem2_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.subitem2_name, "AnyUser", ["read"]),  # by after acl
            (self.subitem2_name, "JoeDoe", ["read"]),  # by after acl
            (self.subitem2_name, "JaneDoe", ["read"]),  # by after acl
        ]

        for itemname, username, may in tests:
            u = User(auth_username=username)
            u.valid = True

            # User should have these rights...
            for right in may:
                can_access = getattr(u.may, right)(itemname)
                assert can_access, f"{u.name!r} may {right} {itemname!r} (normal)"

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents if right not in may]
            for right in mayNot:
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, f"{u.name!r} may not {right} {itemname!r} (normal)"

        # check function rights
        u = User(auth_username="SuperUser")
        assert u.may.superuser()
        u = User(auth_username="SomeGuy")
        assert not u.may.superuser()


class TestItemHierachicalAcls:
    """security: real-life access control list on items testing"""

    mainitem_name = "AclTestMainItem"
    subitem1_name = "AclTestMainItem/SubItem1"
    subitem2_name = "AclTestMainItem/SubItem2"
    item_rwforall = "EveryoneMayReadWriteMe"
    subitem_4boss = "EveryoneMayReadWriteMe/OnlyTheBossMayWMe"
    items = [
        # itemname, acl, content
        (mainitem_name, "JoeDoe: JaneDoe:read,write", "Foo!"),
        # acl None means: "no acl given in item metadata" - this will trigger
        # usage of default acl (non-hierarchical) or usage of default acl and
        # inheritance (hierarchical):
        (subitem1_name, None, "FooFoo!"),
        # acl '' means: "empty acl (no rights for anyone) given" - this will
        # INHIBIT usage of default acl / inheritance (we DO HAVE an item acl,
        # it is just empty!):
        (subitem2_name, "", "BarBar!"),
        (item_rwforall, "All:read,write", "May be read from and written to by anyone"),
        (subitem_4boss, "JoeDoe:read,write", "Only JoeDoe (the boss) may write"),
    ]

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            default_acl = dict(
                hierarchic=True,
                before="WikiAdmin:admin,read,write,create,destroy",
                default="All:read,write",
                after="All:read",
            )

        return Config

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        become_trusted(username="WikiAdmin")
        for item_name, item_acl, item_content in self.items:
            if item_acl is not None:
                update_item(item_name, {ACL: item_acl}, item_content)
            else:
                update_item(item_name, {}, item_content)

    def testItemACLs(self):
        """security: test item acls"""
        tests = [
            # itemname, username, expected_rights
            (self.mainitem_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.mainitem_name, "AnyUser", ["read"]),  # by after acl
            (self.mainitem_name, "JaneDoe", ["read", "write"]),  # by item acl
            (self.mainitem_name, "JoeDoe", []),  # by item acl
            (self.subitem1_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.subitem1_name, "AnyUser", ["read"]),  # by after acl
            (self.subitem1_name, "JoeDoe", []),  # by inherited acl from main item
            (self.subitem1_name, "JaneDoe", ["read", "write"]),  # by inherited acl from main item
            (self.subitem2_name, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),
            (self.subitem2_name, "AnyUser", ["read"]),  # by after acl
            (self.subitem2_name, "JoeDoe", ["read"]),  # by after acl
            (self.subitem2_name, "JaneDoe", ["read"]),  # by after acl
            (self.subitem_4boss, "AnyUser", ["read"]),  # by after acl
            (self.subitem_4boss, "JoeDoe", ["read", "write"]),  # by item acl
        ]

        for itemname, username, may in tests:
            u = User(auth_username=username)
            u.valid = True

            # User should have these rights...
            for right in may:
                can_access = getattr(u.may, right)(itemname)
                assert can_access, f"{u.name!r} may {right} {itemname!r} (hierarchic)"

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents if right not in may]
            for right in mayNot:
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, f"{u.name!r} may not {right} {itemname!r} (hierarchic)"


class TestItemHierachicalAclsMultiItemNames:
    """security: real-life access control list on items testing"""

    # parent / child item names
    p1 = ["p1"]
    c1 = ["p1/c1"]
    p2 = ["p2"]
    c2 = ["p2/c2"]
    c12 = ["p1/c12", "p2/c12"]
    content = b""
    items = [
        # itemnames, acl, content
        (p1, "Editor:", content),  # deny access (due to hierarchic acl mode also effective for children)
        (c1, None, content),  # no own acl -> inherit from parent
        (p2, None, content),  # default acl effective (also for children)
        (c2, None, content),  # no own acl -> inherit from parent
        (c12, None, content),  # no own acl -> inherit from parents
    ]

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            default_acl = dict(
                hierarchic=True,
                before="WikiAdmin:admin,read,write,create,destroy",
                default="Editor:read,write",
                after="All:read",
            )

        return Config

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        become_trusted(username="WikiAdmin")
        for item_names, item_acl, item_content in self.items:
            meta = {NAME: item_names}
            if item_acl is not None:
                meta.update({ACL: item_acl})
            update_item(item_names[0], meta, item_content)

    def testItemACLs(self):
        """security: test item acls"""
        tests = [
            # itemname, username, expected_rights
            (self.p1, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),  # by before acl
            (self.p2, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),  # by before acl
            (self.c1, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),  # by before acl
            (self.c2, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),  # by before acl
            (self.c12, "WikiAdmin", ["read", "write", "admin", "create", "destroy"]),  # by before acl
            (self.p1, "Editor", []),  # by p1 acl
            (self.c1, "Editor", []),  # by p1 acl
            (self.p1, "SomeOne", ["read"]),  # by after acl
            (self.c1, "SomeOne", ["read"]),  # by after acl
            (self.p2, "Editor", ["read", "write"]),  # by default acl
            (self.c2, "Editor", ["read", "write"]),  # by default acl
            (self.p2, "SomeOne", ["read"]),  # by after acl
            (self.c2, "SomeOne", ["read"]),  # by after acl
            (self.c12, "SomeOne", ["read"]),  # by after acl
            # now check the rather special stuff:
            (self.c12, "Editor", ["read", "write"]),  # disallowed via p1, but allowed via p2 via default acl
        ]

        for itemnames, username, may in tests:
            u = User(auth_username=username)
            u.valid = True
            itemname = itemnames[0]

            # User should have these rights...
            for right in may:
                can_access = getattr(u.may, right)(itemname)
                assert can_access, f"{u.name!r} may {right} {itemname!r} (hierarchic)"

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents if right not in may]
            for right in mayNot:
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, f"{u.name!r} may not {right} {itemname!r} (hierarchic)"


# XXX TODO add tests for a user having multiple usernames (one resulting in more permissions than other)

coverage_modules = ["moin.security"]
