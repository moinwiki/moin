# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2009 by ReimarBauer
# Copyright: 2011-2013 by ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.user Tests
"""


from flask import g as flaskg

from moin import user
from moin.items import Item
from moin.constants.keys import ITEMID, NAME, NAMEPREFIX, NAMERE, NAMESPACE, TAGS

import pytest


class TestSimple:
    def test_create_retrieve(self):
        name = "foo"
        password = "barbaz4711"
        email = "foo@example.org"
        # nonexisting user
        u = user.User(name=name, password=password)
        assert u.name == [name]
        assert not u.valid
        assert not u.exists()
        # create a user
        ret = user.create_user(name, password, email, validate=False)
        assert ret is None, f"create_user returned: {ret}"
        # existing user
        u = user.User(name=name, password=password)
        assert u.name == [name]
        assert u.email == email
        assert u.valid
        assert u.exists()


class TestUser:

    @pytest.fixture(autouse=True)
    def saved_user(self):
        orig_user = flaskg.user
        flaskg.user = user.User()
        yield flaskg.user
        flaskg.user = orig_user

    # Passwords / Login -----------------------------------------------

    def testAsciiPassword(self):
        """user: login with ascii password"""
        # Create test user
        name = "__Non Existent User Name__"
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def testUnicodePassword(self):
        """user: login with non-ascii password"""
        # Create test user
        name = "__שם משתמש לא קיים__"  # Hebrew
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def testInvalidatePassword(self):
        """user: test invalidation of password"""
        # Create test user
        name = "__Non Existent User Name__"
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

        # invalidate the stored password (hash)
        theUser.set_password("")  # emptry str or None means "invalidate"
        theUser.save()

        # Try to "login" with previous password
        theUser = user.User(name=name, password=password)
        assert not theUser.valid

        # Try to "login" with empty password
        theUser = user.User(name=name, password="")
        assert not theUser.valid

    def testPasswordHash(self):
        """
        Create user, set a specific pw hash and check that user can login
        with the correct password and can not log in with a wrong password.
        """
        # Create test user
        name = "Test User"
        # sha512_crypt passlib hash for '12345':
        pw_hash = (
            "$6$rounds=1001$y9ObPHKb8cvRCs5G$39IW1i5w6LqXPRi4xqAu3OKv1UO"
            "pVKNkwk7zPnidsKZWqi1CrQBpl2wuq36J/s6yTxjCnmaGzv/2.dAmM8fDY/"
        )
        self.createUser(name, pw_hash, True)

        # Try to "login" with correct password
        theuser = user.User(name=name, password="12345")
        assert theuser.valid

        # Try to "login" with a wrong password
        theuser = user.User(name=name, password="wrong")
        assert not theuser.valid

    # Subscriptions ---------------------------------------------------

    def test_subscriptions(self):
        pagename = "Foo:foo 123"
        tagname = "xxx"
        regexp = r"\d+"
        item = Item.create(pagename)
        item._save({NAMESPACE: "", TAGS: [tagname]})
        item = Item.create(pagename)
        meta = item.meta

        name = "bar"
        password = name
        email = "bar@example.org"
        user.create_user(name, password, email)
        the_user = user.User(name=name, password=password)
        assert not the_user.is_subscribed_to(item)
        the_user.subscribe(NAME, "SomeOtherPageName", "")
        result = the_user.unsubscribe(NAME, "OneMorePageName", "")
        assert result is False

        subscriptions = [
            (ITEMID, meta[ITEMID], None),
            (NAME, pagename, meta[NAMESPACE]),
            (TAGS, tagname, meta[NAMESPACE]),
            (NAMEPREFIX, pagename[:4], meta[NAMESPACE]),
            (NAMERE, regexp, meta[NAMESPACE]),
        ]
        for subscription in subscriptions:
            keyword, value, namespace = subscription
            the_user.subscribe(keyword, value, namespace)
            assert the_user.is_subscribed_to(item)
            the_user.unsubscribe(keyword, value, namespace, item)
            assert not the_user.is_subscribed_to(item)

    # Bookmarks -------------------------------------------------------

    def test_bookmark(self):
        name = "Test_User_bookmark"
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # set / retrieve the bookmark
        bookmark = 1234567
        theUser.bookmark = bookmark
        theUser = user.User(name=name, password=password)
        result = theUser.bookmark
        assert result == bookmark

        # delete the bookmark
        theUser.bookmark = None
        theUser = user.User(name=name, password=password)
        result = theUser.bookmark
        assert result is None

    # Quicklinks ------------------------------------------------------

    def test_quicklinks(self):
        """
        Test for the quicklinks
        """
        pagename = "Test_page_quicklink"
        name = "Test_User_quicklink"
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # no quick links exist yet
        result_before = theUser.quicklinks
        assert result_before == []

        result = theUser.is_quicklinked_to([pagename])
        assert not result

        # add quicklink
        theUser.quicklink("Test_page_added")
        result_on_addition = theUser.quicklinks
        expected = ["MoinTest/Test_page_added"]
        assert result_on_addition == expected

        # remove quicklink
        theUser.quickunlink("Test_page_added")
        result_on_removal = theUser.quicklinks
        expected = []
        assert result_on_removal == expected

    # Trail -----------------------------------------------------------

    def test_trail(self):
        name = "Test_User_trail"
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # no item name added to trail
        result = theUser.get_trail()
        expected = []
        assert result == expected

        # item name added to trail
        theUser.add_trail("item_added")
        theUser = user.User(name=name, password=password)
        result = theUser.get_trail()
        expected = ["MoinTest/item_added"]
        assert result == expected

    # Sessions -------------------------------------------------------

    def test_sessions(self):
        name = "Test_User_sessions"
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # generate test token and validate it
        test_token = theUser.generate_session_token()
        result_success = theUser.validate_session(test_token)
        assert result_success

        # check if the token is saved
        test_new_token = theUser.get_session_token()
        assert test_token == test_new_token

        # check if password change invalidates the token
        theUser.set_password(password, False)
        result_failure = theUser.validate_session(test_token)
        assert not result_failure

    # Other ----------------------------------------------------------

    def test_recovery_token(self):
        name = "Test_User_other"
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # use recovery token to generate new password
        test_token = theUser.generate_recovery_token()
        result_success = theUser.apply_recovery_token(test_token, "test_newpass")
        assert result_success

        # wrong token
        result_failure = theUser.apply_recovery_token("test_wrong_token", "test_newpass")
        assert not result_failure

    # Helpers ---------------------------------------------------------

    def createUser(self, name, password, pwencoded=False, email=None, validate=False):
        ret = user.create_user(name, password, email, validate=validate, is_encrypted=pwencoded)
        assert ret is None, f"create_user returned: {ret}"


class TestGroupName:

    def testGroupNames(self):
        """user: isValidName: reject group names"""
        test = "AdminGroup"
        assert not user.isValidName(test)


class TestIsValidName:

    def testNonAlnumCharacters(self):
        """user: isValidName: reject unicode non alpha numeric characters

        : and , used in acl rules, we might add more characters to the syntax.
        """
        invalid = '! # $ % ^ & * ( ) = + , : ; " | ~ / \\ \u0000 \u202a'.split()
        base = "User{0}Name"
        for c in invalid:
            name = base.format(c)
            assert not user.isValidName(name)

    def testWhitespace(self):
        """user: isValidName: reject leading, trailing or multiple whitespace"""
        cases = (" User Name", "User Name ", "User   Name")
        for test in cases:
            assert not user.isValidName(test)

    def testValid(self):
        """user: isValidName: accept names in any language, with spaces"""
        cases = (
            "Jürgen Hermann",  # German
            "ניר סופר",  # Hebrew
            "CamelCase",  # Good old camel case
            "가각간갇갈 갉갊감 갬갯걀갼",  # Hangul (gibberish)
        )
        for test in cases:
            assert user.isValidName(test)


coverage_modules = ["moin.user"]
