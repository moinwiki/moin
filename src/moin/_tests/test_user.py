# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2009 by ReimarBauer
# Copyright: 2011-2013 by ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.user tests.
"""

import pytest

from moin import flaskg
from moin.constants.itemtypes import ITEMTYPE_DEFAULT, ITEMTYPE_USERPROFILE
from moin.constants.keys import ITEMID, ITEMTYPE, NAME, NAMEPREFIX, NAMERE, NAMESPACE, REV_NUMBER, TAGS
from moin.items import Item
from moin.user import create_user, is_valid_username, User


@pytest.mark.usefixtures("_req_ctx")
class TestSimple:
    def test_create_retrieve(self):
        name = "foo"
        password = "barbaz4711"
        email = "foo@example.org"
        # nonexisting user
        user = User(name=name, password=password)
        assert user.name == [name]
        assert not user.valid
        assert not user.exists()
        # create a user
        ret = create_user(name, password, email, validate=False)
        assert ret is None, f"create_user returned: {ret}"
        # existing user
        user = User(name=name, password=password)
        assert user.name == [name]
        assert user.email == email
        assert user.valid
        assert user.exists()
        assert user.profile[ITEMTYPE] == ITEMTYPE_USERPROFILE
        assert user.profile[REV_NUMBER] == 1


@pytest.mark.usefixtures("_req_ctx", "saved_user")
class TestUser:

    @pytest.fixture
    def saved_user(self):
        orig_user = flaskg.user
        flaskg.user = User()
        yield flaskg.user
        flaskg.user = orig_user

    # Passwords / Login -----------------------------------------------

    def testAsciiPassword(self):
        """User: login with ASCII password."""
        # Create test user
        name = "__Non Existent User Name__"
        password = name
        self.createUser(name, password)

        # Try to "login"
        user = User(name=name, password=password)
        assert user.valid

    def testUnicodePassword(self):
        """User: login with non-ASCII password."""
        # Create test user
        name = "__שם משתמש לא קיים__"  # Hebrew
        password = name
        self.createUser(name, password)

        # Try to "login"
        user = User(name=name, password=password)
        assert user.valid

    def testInvalidatePassword(self):
        """User: test invalidation of password."""
        # Create test user
        name = "__Non Existent User Name__"
        password = name
        self.createUser(name, password)

        # Try to "login"
        user = User(name=name, password=password)
        assert user.valid

        # Invalidate the stored password (hash)
        user.set_password("")  # empty str or None means "invalidate"
        user.save()

        # Try to "login" with previous password
        user = User(name=name, password=password)
        assert not user.valid

        # Try to "login" with empty password
        user = User(name=name, password="")
        assert not user.valid

    def testPasswordHash(self):
        """
        Create a user, set a specific password hash, and check that the user can log in
        with the correct password and cannot log in with a wrong password.
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
        user = User(name=name, password="12345")
        assert user.valid

        # Try to "login" with a wrong password
        user = User(name=name, password="wrong")
        assert not user.valid

    # Subscriptions ---------------------------------------------------

    def test_subscriptions(self):
        pagename = "Foo:foo 123"
        tagname = "xxx"
        regexp = r"\d+"
        item = Item.create(pagename)
        item._save({NAMESPACE: "", TAGS: [tagname], ITEMTYPE: ITEMTYPE_DEFAULT})
        item = Item.create(pagename)
        meta = item.meta

        name = "bar"
        password = name
        email = "bar@example.org"
        create_user(name, password, email)
        user = User(name=name, password=password)
        assert not user.is_subscribed_to(item)
        user.subscribe(NAME, "SomeOtherPageName", "")
        result = user.unsubscribe(NAME, "OneMorePageName", "")
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
            user.subscribe(keyword, value, namespace)
            assert user.is_subscribed_to(item)
            user.unsubscribe(keyword, value, namespace, item)
            assert not user.is_subscribed_to(item)

    # Bookmarks -------------------------------------------------------

    def test_bookmark(self):
        name = "Test_User_bookmark"
        password = name
        self.createUser(name, password)
        user = User(name=name, password=password)

        # set / retrieve the bookmark
        bookmark = 1234567
        user.bookmark = bookmark
        user = User(name=name, password=password)
        result = user.bookmark
        assert result == bookmark

        # delete the bookmark
        user.bookmark = None
        user = User(name=name, password=password)
        result = user.bookmark
        assert result is None

    # Quicklinks ------------------------------------------------------

    def test_quicklinks(self):
        """
        Test quicklinks.
        """
        pagename = "Test_page_quicklink"
        name = "Test_User_quicklink"
        password = name
        self.createUser(name, password)
        user = User(name=name, password=password)

        # no quick links exist yet
        result_before = user.quicklinks
        assert result_before == []

        result = user.is_quicklinked_to([pagename])
        assert not result

        # add quicklink
        user.quicklink("Test_page_added")
        result_on_addition = user.quicklinks
        expected = ["MoinTest/Test_page_added"]
        assert result_on_addition == expected

        # remove quicklink
        user.quickunlink("Test_page_added")
        result_on_removal = user.quicklinks
        expected = []
        assert result_on_removal == expected

    # Trail -----------------------------------------------------------

    def test_trail(self):
        name = "Test_User_trail"
        password = name
        self.createUser(name, password)
        user = User(name=name, password=password)

        # no item name added to trail
        result = user.get_trail()
        expected = []
        assert result == expected

        # item name added to trail
        user.add_trail("item_added", [])
        user = User(name=name, password=password)
        result = user.get_trail()
        expected = [("MoinTest/item_added", [])]
        assert result == expected

    # Sessions -------------------------------------------------------

    def test_sessions(self):
        name = "Test_User_sessions"
        password = name
        self.createUser(name, password)
        user = User(name=name, password=password)

        # generate test token and validate it
        test_token = user.generate_session_token()
        result_success = user.validate_session(test_token)
        assert result_success

        # check if the token is saved
        test_new_token = user.get_session_token()
        assert test_token == test_new_token

        # check if password change invalidates the token
        user.set_password(password, False)
        result_failure = user.validate_session(test_token)
        assert not result_failure

    # Other ----------------------------------------------------------

    def test_recovery_token(self):
        name = "Test_User_other"
        password = name
        self.createUser(name, password)
        user = User(name=name, password=password)

        # use recovery token to generate new password
        test_token = user.generate_recovery_token()
        result_success = user.apply_recovery_token(test_token, "test_newpass")
        assert result_success

        # wrong token
        result_failure = user.apply_recovery_token("test_wrong_token", "test_newpass")
        assert not result_failure

    # Helpers ---------------------------------------------------------

    def createUser(self, name, password, pwencoded=False, email=None, validate=False):
        ret = create_user(name, password, email, validate=validate, is_encrypted=pwencoded)
        assert ret is None, f"create_user returned: {ret}"


class TestGroupName:

    @pytest.mark.usefixtures("_app_ctx")
    def test_group_names(self):
        """is_valid_username: reject group names."""
        test = "AdminGroup"
        assert not is_valid_username(test)


@pytest.mark.usefixtures("_app_ctx")
class TestIsValidUserName:

    def test_non_alnum_characters(self):
        """User: is_valid_username: reject Unicode non-alphanumeric characters.

        ':' and ',' are used in ACL rules; we might add more characters to the syntax.
        """
        invalid = '! # $ % ^ & * ( ) = + , : ; " | ~ / \\ \u0000 \u202a'.split()
        base = "User{0}Name"
        for c in invalid:
            name = base.format(c)
            assert not is_valid_username(name)

    def test_whitespace(self):
        """is_valid_username: reject leading, trailing, or multiple whitespace."""
        cases = (" User Name", "User Name ", "User   Name")
        for test in cases:
            assert not is_valid_username(test)

    def test_valid(self):
        """is_valid_username: accept names in any language, with spaces."""
        cases = (
            "Jürgen Hermann",  # German
            "ניר סופר",  # Hebrew
            "CamelCase",  # Good old camel case
            "가각간갇갈 갉갊감 갬갯걀갼",  # Hangul (gibberish)
        )
        for test in cases:
            assert is_valid_username(test)


coverage_modules = ["moin.user"]
