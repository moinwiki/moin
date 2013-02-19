# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2007 by MoinMoin:ReimarBauer
# Copyright: 2007,2009 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.security Tests
"""


import pytest

from flask import current_app as app

from MoinMoin.security import AccessControlList, ACLStringIterator

from MoinMoin.user import User
from MoinMoin.constants.keys import NAME, ACL
from MoinMoin.datastruct import ConfigGroups

from MoinMoin._tests import update_item
from MoinMoin._tests import become_trusted


def acliter(acl):
    """
    return a acl string iterator (using cfg.acl_rights_contents as valid acl rights)
    """
    return ACLStringIterator(app.cfg.acl_rights_contents, acl)


class TestACLStringIterator(object):

    def testEmpty(self):
        """ security: empty acl string raise StopIteration """
        acl_iter = acliter('')
        pytest.raises(StopIteration, acl_iter.next)

    def testWhiteSpace(self):
        """ security: white space acl string raise StopIteration """
        acl_iter = acliter('       ')
        pytest.raises(StopIteration, acl_iter.next)

    def testDefault(self):
        """ security: default meta acl """
        acl_iter = acliter('Default Default')
        for mod, entries, rights in acl_iter:
            assert entries == ['Default']
            assert rights == []

    def testEmptyRights(self):
        """ security: empty rights """
        acl_iter = acliter('WikiName:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['WikiName']
        assert rights == []

    def testSingleWikiNameSingleRight(self):
        """ security: single wiki name, single right """
        acl_iter = acliter('WikiName:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['WikiName']
        assert rights == ['read']

    def testMultipleWikiNameAndRights(self):
        """ security: multiple wiki names and rights """
        acl_iter = acliter('UserOne,UserTwo:read,write')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne', 'UserTwo']
        assert rights == ['read', 'write']

    def testMultipleWikiNameAndRightsSpaces(self):
        """ security: multiple names with spaces """
        acl_iter = acliter('user one,user two:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one', 'user two']
        assert rights == ['read']

    def testMultipleEntries(self):
        """ security: multiple entries """
        acl_iter = acliter('UserOne:read,write UserTwo:read All:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserTwo']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []

    def testNameWithSpaces(self):
        """ security: single name with spaces """
        acl_iter = acliter('user one:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one']
        assert rights == ['read']

    def testMultipleEntriesWithSpaces(self):
        """ security: multiple entries with spaces """
        acl_iter = acliter('user one:read,write user two:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user two']
        assert rights == ['read']

    def testMixedNames(self):
        """ security: mixed wiki names and names with spaces """
        acl_iter = acliter('UserOne,user two:read,write user three,UserFour:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']

    def testModifier(self):
        """ security: acl modifiers """
        acl_iter = acliter('+UserOne:read -UserTwo:')
        mod, entries, rights = acl_iter.next()
        assert mod == '+'
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert mod == '-'
        assert entries == ['UserTwo']
        assert rights == []

    def testIgnoreInvalidACL(self):
        """ security: ignore invalid acl

        The last part of this acl can not be parsed. If it ends with :
        then it will be parsed as one name with spaces.
        """
        acl_iter = acliter('UserOne:read user two is ignored')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        pytest.raises(StopIteration, acl_iter.next)

    def testEmptyNamesWithRight(self):
        """ security: empty names with rights

        The documents does not talk about this case, may() should ignore
        the rights because there is no entry.
        """
        acl_iter = acliter('UserOne:read :read All:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == []
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []

    def testIgnoreInvalidRights(self):
        """ security: ignore rights not in acl_rights_contents

        Note: this is also important for ACL regeneration (see also acl
              regeneration test for storage.backends.fs19).
        """
        acl_iter = acliter('UserOne:read,sing,write,drink,sleep')
        mod, entries, rights = acl_iter.next()
        assert rights == ['read', 'write']

        # we use strange usernames that include invalid rights as substrings
        acls = list(acliter(u"JimAdelete,JoeArevert:admin,read,delete,write,revert"))
        # now check that we have lost the invalid rights 'delete' and 'revert',
        # but the usernames should be still intact.
        assert acls == [('', [u'JimAdelete', u'JoeArevert'], ['admin', 'read', 'write', ])]

    def testBadGuy(self):
        """ security: bad guy may not allowed anything

        This test was failing on the apply acl rights test.
        """
        acl_iter = acliter('UserOne:read,write BadGuy: All:read')
        mod, entries, rights = acl_iter.next()
        mod, entries, rights = acl_iter.next()
        assert entries == ['BadGuy']
        assert rights == []

    def testAllowExtraWhitespace(self):
        """ security: allow extra white space between entries """
        acl_iter = acliter('UserOne,user two:read,write   user three,UserFour:read  All:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []


class TestAcl(object):
    """ security: testing access control list

    TO DO: test unknown user?
    """
    def testhasACL(self):
        acl = AccessControlList(valid=app.cfg.acl_rights_contents)
        assert not acl.has_acl()
        acl = AccessControlList(["All:read", ], valid=app.cfg.acl_rights_contents)
        assert acl.has_acl()

    def testApplyACLByUser(self):
        """ security: applying acl by user name"""
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
            ('Admin1', ('read', 'write', 'admin')),
            ('Admin2', ('read', 'write', 'admin')),
            ('Admin3', ('read', 'write', 'admin')),
            ('JoeDoe', ('read', 'write')),
            ('SomeGuy', ('read', )),
            # Extended names or mix of extended and CamelCase
            ('name with spaces', ('read', 'write', )),
            ('another one', ('read', 'write', )),
            ('CamelCase', ('read', 'write', )),
            ('extended name', ('read', 'write', )),
            # Blocking bad guys
            ('BadGuy', ()),
            # All other users - every one not mentioned in the acl lines
            ('All', ('read', )),
            ('Anonymous', ('read', )),
            # we check whether ACL processing stops for a user/right match
            # with ACL modifiers
            ('MinusGuy', ()),
            ('PlusGuy', ('read', )),
        )

        # Check rights
        for user, may in users:
            mayNot = [right for right in app.cfg.acl_rights_contents
                      if right not in may]
            # User should have these rights...
            for right in may:
                assert acl.may(user, right)
            # But NOT these:
            for right in mayNot:
                assert not acl.may(user, right)


class TestGroupACL(object):

    from MoinMoin._tests import wikiconfig

    class Config(wikiconfig.Config):
        def groups(cfg):
            groups = {
                u'PGroup': frozenset([u'Antony', u'Beatrice', ]),
                u'AGroup': frozenset([u'All', ]),
                # note: the next line is a INTENDED misnomer, there is "All" in
                # the group NAME, but not in the group members. This makes
                # sure that a bug that erroneously checked "in groupname" (instead
                # of "in groupmembers") does not reappear.
                u'AllGroup': frozenset([]),  # note: intended misnomer
            }
            return ConfigGroups(groups)

    def testApplyACLByGroup(self):
        """ security: applying acl by group name"""
        # This acl string...
        acl_rights = [
            "PGroup,AllGroup:read,write,admin "
            "AGroup:read "
        ]
        acl = AccessControlList(acl_rights, valid=app.cfg.acl_rights_contents)

        # Should apply these rights:
        users = (
            # user, rights
            ('Antony', ('read', 'write', 'admin', )),  # in PGroup
            ('Beatrice', ('read', 'write', 'admin', )),  # in PGroup
            ('Charles', ('read', )),  # virtually in AGroup
        )

        # Check rights
        for user, may in users:
            mayNot = [right for right in app.cfg.acl_rights_contents
                      if right not in may]
            # User should have these rights...
            for right in may:
                assert acl.may(user, right)
            # But NOT these:
            for right in mayNot:
                assert not acl.may(user, right)


class TestItemAcls(object):
    """ security: real-life access control list on items testing
    """
    mainitem_name = u'AclTestMainItem'
    subitem1_name = u'AclTestMainItem/SubItem1'
    subitem2_name = u'AclTestMainItem/SubItem2'
    item_rwforall = u'EveryoneMayReadWriteMe'
    subitem_4boss = u'EveryoneMayReadWriteMe/OnlyTheBossMayWMe'
    items = [
        # itemname, acl, content
        (mainitem_name, u'JoeDoe: JaneDoe:read,write', u'Foo!'),
        # acl None means: "no acl given in item metadata" - this will trigger
        # usage of default acl (non-hierarchical) or usage of default acl and
        # inheritance (hierarchical):
        (subitem1_name, None, u'FooFoo!'),
        # acl u'' means: "empty acl (no rights for noone) given" - this will
        # INHIBIT usage of default acl / inheritance (we DO HAVE an item acl,
        # it is just empty!):
        (subitem2_name, u'', u'BarBar!'),
        (item_rwforall, u'All:read,write', u'May be read from and written to by anyone'),
        (subitem_4boss, u'JoeDoe:read,write', u'Only JoeDoe (the boss) may write'),
    ]

    from MoinMoin._tests import wikiconfig

    class Config(wikiconfig.Config):
        content_acl = dict(hierarchic=False, before=u"WikiAdmin:admin,read,write,create,destroy", default=u"All:read,write", after=u"All:read")
        acl_functions = u"SuperUser:superuser NoTextchaUser:notextcha"

    def setup_method(self, method):
        become_trusted(username=u'WikiAdmin')
        for item_name, item_acl, item_content in self.items:
            if item_acl is not None:
                update_item(item_name, {ACL: item_acl}, item_content)
            else:
                update_item(item_name, {}, item_content)

    def testItemACLs(self):
        """ security: test item acls """
        tests = [
            # itemname, username, expected_rights
            (self.mainitem_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.mainitem_name, u'AnyUser', ['read']),  # by after acl
            (self.mainitem_name, u'JaneDoe', ['read', 'write']),  # by item acl
            (self.mainitem_name, u'JoeDoe', []),  # by item acl
            (self.subitem1_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.subitem1_name, u'AnyUser', ['read', 'write']),  # by default acl
            (self.subitem1_name, u'JoeDoe', ['read', 'write']),  # by default acl
            (self.subitem1_name, u'JaneDoe', ['read', 'write']),  # by default acl
            (self.subitem2_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.subitem2_name, u'AnyUser', ['read']),  # by after acl
            (self.subitem2_name, u'JoeDoe', ['read']),  # by after acl
            (self.subitem2_name, u'JaneDoe', ['read']),  # by after acl
        ]

        for itemname, username, may in tests:
            u = User(auth_username=username)
            u.valid = True

            def _have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert can_access, "{0!r} may {1} {2!r} (normal)".format(u.name, right, itemname)

            # User should have these rights...
            for right in may:
                yield _have_right, u, right, itemname

            def _not_have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, "{0!r} may not {1} {2!r} (normal)".format(u.name, right, itemname)

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents
                      if right not in may]
            for right in mayNot:
                yield _not_have_right, u, right, itemname

        # check function rights
        u = User(auth_username='SuperUser')
        assert u.may.superuser()
        u = User(auth_username='NoTextchaUser')
        assert u.may.notextcha()
        u = User(auth_username='SomeGuy')
        assert not u.may.superuser()
        assert not u.may.notextcha()


class TestItemHierachicalAcls(object):
    """ security: real-life access control list on items testing
    """
    mainitem_name = u'AclTestMainItem'
    subitem1_name = u'AclTestMainItem/SubItem1'
    subitem2_name = u'AclTestMainItem/SubItem2'
    item_rwforall = u'EveryoneMayReadWriteMe'
    subitem_4boss = u'EveryoneMayReadWriteMe/OnlyTheBossMayWMe'
    items = [
        # itemname, acl, content
        (mainitem_name, u'JoeDoe: JaneDoe:read,write', u'Foo!'),
        # acl None means: "no acl given in item metadata" - this will trigger
        # usage of default acl (non-hierarchical) or usage of default acl and
        # inheritance (hierarchical):
        (subitem1_name, None, u'FooFoo!'),
        # acl u'' means: "empty acl (no rights for noone) given" - this will
        # INHIBIT usage of default acl / inheritance (we DO HAVE an item acl,
        # it is just empty!):
        (subitem2_name, u'', u'BarBar!'),
        (item_rwforall, u'All:read,write', u'May be read from and written to by anyone'),
        (subitem_4boss, u'JoeDoe:read,write', u'Only JoeDoe (the boss) may write'),
    ]

    from MoinMoin._tests import wikiconfig

    class Config(wikiconfig.Config):
        content_acl = dict(hierarchic=True, before=u"WikiAdmin:admin,read,write,create,destroy", default=u"All:read,write", after=u"All:read")

    def setup_method(self, method):
        become_trusted(username=u'WikiAdmin')
        for item_name, item_acl, item_content in self.items:
            if item_acl is not None:
                update_item(item_name, {ACL: item_acl}, item_content)
            else:
                update_item(item_name, {}, item_content)

    def testItemACLs(self):
        """ security: test item acls """
        tests = [
            # itemname, username, expected_rights
            (self.mainitem_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.mainitem_name, u'AnyUser', ['read']),  # by after acl
            (self.mainitem_name, u'JaneDoe', ['read', 'write']),  # by item acl
            (self.mainitem_name, u'JoeDoe', []),  # by item acl
            (self.subitem1_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.subitem1_name, u'AnyUser', ['read']),  # by after acl
            (self.subitem1_name, u'JoeDoe', []),  # by inherited acl from main item
            (self.subitem1_name, u'JaneDoe', ['read', 'write']),  # by inherited acl from main item
            (self.subitem2_name, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),
            (self.subitem2_name, u'AnyUser', ['read']),  # by after acl
            (self.subitem2_name, u'JoeDoe', ['read']),  # by after acl
            (self.subitem2_name, u'JaneDoe', ['read']),  # by after acl
            (self.subitem_4boss, u'AnyUser', ['read']),  # by after acl
            (self.subitem_4boss, u'JoeDoe', ['read', 'write']),  # by item acl
        ]

        for itemname, username, may in tests:
            u = User(auth_username=username)
            u.valid = True

            def _have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert can_access, "{0!r} may {1} {2!r} (hierarchic)".format(u.name, right, itemname)

            # User should have these rights...
            for right in may:
                yield _have_right, u, right, itemname

            def _not_have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, "{0!r} may not {1} {2!r} (hierarchic)".format(u.name, right, itemname)

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents
                      if right not in may]
            for right in mayNot:
                yield _not_have_right, u, right, itemname


class TestItemHierachicalAclsMultiItemNames(object):
    """ security: real-life access control list on items testing
    """
    # parent / child item names
    p1 = [u'p1', ]
    c1 = [u'p1/c1', ]
    p2 = [u'p2', ]
    c2 = [u'p2/c2', ]
    c12 = [u'p1/c12', u'p2/c12', ]
    items = [
        # itemnames, acl, content
        (p1, u'Editor:', p1),  # deny access (due to hierarchic acl mode also effective for children)
        (c1, None, c1),  # no own acl -> inherit from parent
        (p2, None, p2),  # default acl effective (also for children)
        (c2, None, c2),  # no own acl -> inherit from parent
        (c12, None, c12),  # no own acl -> inherit from parents
    ]

    from MoinMoin._tests import wikiconfig

    class Config(wikiconfig.Config):
        content_acl = dict(hierarchic=True, before=u"WikiAdmin:admin,read,write,create,destroy", default=u"Editor:read,write", after=u"All:read")

    def setup_method(self, method):
        become_trusted(username=u'WikiAdmin')
        for item_names, item_acl, item_content in self.items:
            meta = {NAME: item_names}
            if item_acl is not None:
                meta.update({ACL: item_acl})
            update_item(item_names[0], meta, item_content)

    def testItemACLs(self):
        """ security: test item acls """
        tests = [
            # itemname, username, expected_rights
            (self.p1, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),  # by before acl
            (self.p2, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),  # by before acl
            (self.c1, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),  # by before acl
            (self.c2, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),  # by before acl
            (self.c12, u'WikiAdmin', ['read', 'write', 'admin', 'create', 'destroy']),  # by before acl
            (self.p1, u'Editor', []),  # by p1 acl
            (self.c1, u'Editor', []),  # by p1 acl
            (self.p1, u'SomeOne', ['read']),  # by after acl
            (self.c1, u'SomeOne', ['read']),  # by after acl
            (self.p2, u'Editor', ['read', 'write']),  # by default acl
            (self.c2, u'Editor', ['read', 'write']),  # by default acl
            (self.p2, u'SomeOne', ['read']),  # by after acl
            (self.c2, u'SomeOne', ['read']),  # by after acl
            (self.c12, u'SomeOne', ['read']),  # by after acl
            # now check the rather special stuff:
            (self.c12, u'Editor', ['read', 'write']),  # disallowed via p1, but allowed via p2 via default acl
        ]

        for itemnames, username, may in tests:
            u = User(auth_username=username)
            u.valid = True
            itemname = itemnames[0]

            def _have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert can_access, "{0!r} may {1} {2!r} (hierarchic)".format(u.name, right, itemname)

            # User should have these rights...
            for right in may:
                yield _have_right, u, right, itemname

            def _not_have_right(u, right, itemname):
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, "{0!r} may not {1} {2!r} (hierarchic)".format(u.name, right, itemname)

            # User should NOT have these rights:
            mayNot = [right for right in app.cfg.acl_rights_contents
                      if right not in may]
            for right in mayNot:
                yield _not_have_right, u, right, itemname


# XXX TODO add tests for a user having multiple usernames (one resulting in more permissions than other)

coverage_modules = ['MoinMoin.security']
