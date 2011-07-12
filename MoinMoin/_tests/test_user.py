# -*- coding: utf-8 -*-
# Copyright: 2003-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2009 by ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.user Tests
"""


import pytest

from flask import current_app as app
from flask import g as flaskg

from MoinMoin import user
from MoinMoin.util import crypto


class TestLoginWithPassword(object):
    """user: login tests"""

    def setup_method(self, method):
        # Save original user
        self.saved_user = flaskg.user

        # Create anon user for the tests
        flaskg.user = user.User()

        self.user = None

    def teardown_method(self, method):
        """ Run after each test

        Remove user and reset user listing cache.
        """
        # Remove user file and user
        if self.user is not None:
            del self.user

        # Restore original user
        flaskg.user = self.saved_user

    def testAsciiPassword(self):
        """ user: login with ascii password """
        # Create test user
        name = u'__Non Existent User Name__'
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def testUnicodePassword(self):
        """ user: login with non-ascii password """
        # Create test user
        name = u'__שם משתמש לא קיים__' # Hebrew
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def test_auth_with_ssha_stored_password(self):
        """
        Create user with {SSHA} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # pass = 12345
        # salt = salt
        password = '{SSHA}x4YEGdfI4i0qROaY3NTHCmwSJY5zYWx0'
        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_auth_with_apr1_stored_password(self):
        """
        Create user with {APR1} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbm blaze 12345"
        password = '{APR1}$apr1$NG3VoiU5$PSpHT6tV0ZMKkSZ71E3qg.' # 12345
        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_auth_with_md5_stored_password(self):
        """
        Create user with {MD5} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        password = '{MD5}$1$salt$etVYf53ma13QCiRbQOuRk/' # 12345
        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_auth_with_des_stored_password(self):
        """
        Create user with {DES} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbd blaze 12345"
        password = '{DES}gArsfn7O5Yqfo' # 12345
        self.createUser(name, password, True)

        try:
            import crypt
            # Try to "login"
            theuser = user.User(name=name, password='12345')
            assert theuser.valid
        except ImportError:
            pytest.skip("Platform does not provide crypt module!")

    def test_auth_with_ssha256_stored_password(self):
        """
        Create user with {SSHA256} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with online sha256 tool
        # pass: 12345
        # salt: salt
        # base64 encoded
        password = '{SSHA256}r4ONZUfEyn9MUkcyDQkQ5MBNpdIerM24MasxFpuQBaFzYWx0'

        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_regression_user_password_started_with_sha(self):
        # This is regression test for bug in function 'user.create_user'.
        #
        # This function does not encode passwords which start with '{SHA}'
        # It treats them as already encoded SHA hashes.
        #
        # If user during registration specifies password starting with '{SHA}'
        # this password will not get encoded and user object will get saved with empty enc_password
        # field.
        #
        # Such situation leads to "KeyError: 'enc_password'" during
        # user authentication.

        # Any Password begins with the {SHA} symbols led to
        # "KeyError: 'enc_password'" error during user authentication.
        user_name = u'moin'
        user_password = u'{SHA}LKM56'
        user.create_user(user_name, user_password, u'moin@moinmo.in', '')

        # Try to "login"
        theuser = user.User(name=user_name, password=user_password)
        assert theuser.valid

    def testSubscriptionSubscribedPage(self):
        """ user: tests isSubscribedTo  """
        pagename = u'HelpMiscellaneous'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert theUser.isSubscribedTo([pagename]) # list(!) of pages to check

    def testSubscriptionSubPage(self):
        """ user: tests isSubscribedTo on a subpage """
        pagename = u'HelpMiscellaneous'
        testPagename = u'HelpMiscellaneous/FrequentlyAskedQuestions'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert not theUser.isSubscribedTo([testPagename]) # list(!) of pages to check

    def testRenameUser(self):
        """ create user and then rename user and check if it still
        exists under old name
        """
        # Create test user
        name = u'__Some Name__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name)
        # Rename user
        theUser.name = u'__SomeName__'
        theUser.save()
        theUser = user.User(name=name, password=password)

        assert not theUser.exists()

    def test_upgrade_password_from_ssha_to_ssha256(self):
        """
        Create user with {SSHA} password and check that logging in
        upgrades to {SSHA256}.
        """
        name = u'/no such user/'
        #pass = MoinMoin
        #salr = 12345
        password = '{SSHA}xkDIIx1I7A4gC98Vt/+UelIkTDYxMjM0NQ=='
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:9] == '{SSHA256}'

    def test_upgrade_password_from_sha_to_ssha256(self):
        """
        Create user with {SHA} password and check that logging in
        upgrades to {SSHA256}.
        """
        name = u'/no such user/'
        password = '{SHA}jLIjfQZ5yojbZGTqxg2pY0VROWQ=' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:9] == '{SSHA256}'

    def test_upgrade_password_from_apr1_to_ssha256(self):
        """
        Create user with {APR1} password and check that logging in
        upgrades to {SSHA256}.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbm blaze 12345"
        password = '{APR1}$apr1$NG3VoiU5$PSpHT6tV0ZMKkSZ71E3qg.' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:9] == '{SSHA256}'

    def test_upgrade_password_from_md5_to_ssha256(self):
        """
        Create user with {MD5} password and check that logging in
        upgrades to {SSHA}.
        """
        # Create test user
        name = u'Test User'
        password = '{MD5}$1$salt$etVYf53ma13QCiRbQOuRk/' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:9] == '{SSHA256}'

    def test_upgrade_password_from_des_to_ssha256(self):
        """
        Create user with {DES} password and check that logging in
        upgrades to {SSHA}.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbd blaze 12345"
        password = '{DES}gArsfn7O5Yqfo' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:9] == '{SSHA256}'

    def test_for_email_attribute_by_name(self):
        """
        checks for no access to the email attribute by getting the user object from name
        """
        name = u"__TestUser__"
        password = u"ekfdweurwerh"
        email = u"__TestUser__@moinhost"
        self.createUser(name, password, email=email)
        theuser = user.User(name=name)
        assert theuser.email is None

    def test_for_email_attribut_by_uid(self):
        """
        checks access to the email attribute by getting the user object from the uid
        """
        name = u"__TestUser2__"
        password = u"ekERErwerwerh"
        email = u"__TestUser2__@moinhost"
        self.createUser(name, password, email=email)
        uid = user.getUserId(name)
        theuser = user.User(uid)
        assert theuser.email == email

    # Bookmarks -------------------------------------------------------

    def test_bookmark(self):
        name = u'Test_User_quicklink'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        theUser.setBookmark(7)
        result_added = theUser.getBookmark()
        expected = 7
        assert result_added == expected, ('Expected "%(expected)s" but got "%(result_added)s"') % locals()
        # delete the bookmark
        result_success = theUser.delBookmark()
        assert result_success == 0
        result_deleted = theUser.getBookmark()
        assert not result_deleted

        # delBookmark should return 1 on failure
        result_failure = theUser.delBookmark()
        assert result_failure == 1

    # Quicklinks ------------------------------------------------------

    def test_quicklinks(self):
        """
        Test for the quicklinks
        """
        pagename = u'Test_page_quicklink'
        name = u'Test_User_quicklink'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)

        # no quick links exist yet
        result_before = theUser.getQuickLinks()
        assert result_before == []

        result = theUser.isQuickLinkedTo([pagename])
        assert not result

        # quicklinks for the user - theUser exist now
        theUser.quicklinks = [pagename]
        result_after = theUser.getQuickLinks()
        expected = [u'Test_page_quicklink']
        assert result_after == expected, ('Expected "%(expected)s" but got "%(result_after)s"') % locals()

        # test for addQuicklink()
        theUser.addQuicklink(u'Test_page_added')
        result_on_addition = theUser.getQuickLinks()
        expected = [u'Test_page_quicklink', u'Test_page_added']
        assert result_on_addition == expected, ('Expected "%(expected)s" but got "%(result_on_addition)s"') % locals()

        # user should be quicklinked to [pagename]
        result = theUser.isQuickLinkedTo([pagename])
        assert result

        # previously added page u'Test_page_added' is removed
        theUser.removeQuicklink(u'Test_page_added')
        result_on_removal = theUser.getQuickLinks()
        expected = [u'Test_page_quicklink']
        assert result_on_removal == expected, ('Expected "%(expected)s" but got "%(result_on_removal)s"') % locals()

    # Trail -----------------------------------------------------------

    def test_trail(self):
        pagename = u'Test_page_trail'
        name = u'Test_User_trail'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # no item name added to trail
        result = theUser.getTrail()
        expected = []
        assert result == expected

        # item name added to trail
        theUser.addTrail(u'item_added')
        result = theUser.getTrail()
        expected = [u'item_added']
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

    # Other ----------------------------------------------------------

    def test_signature(self):
        name = u'Test_User_other'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # test the user signature
        result = theUser.signature()
        expected =  u'[[Test_User_other]]'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

    def test_recovery_token(self):
        name = u'Test_User_other'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # use recovery token to generate new password
        test_token = theUser.generate_recovery_token()
        result_success = theUser.apply_recovery_token(test_token, u'test_newpass')
        assert result_success

        # wrong token
        result_failure = theUser.apply_recovery_token('test_wrong_token', u'test_newpass')
        assert not result_failure

    # Helpers ---------------------------------------------------------

    def createUser(self, name, password, pwencoded=False, email=None):
        """ helper to create test user
        """
        # Create user
        self.user = user.User()
        self.user.name = name
        self.user.email = email
        if not pwencoded:
            password = crypto.crypt_password(password)
        self.user.enc_password = password

        # Validate that we are not modifying existing user data file!
        if self.user.exists():
            self.user = None
            pytest.skip("Test user exists, will not override existing user data file!")

        # Save test user
        self.user.save()

        # Validate user creation
        if not self.user.exists():
            self.user = None
            pytest.skip("Can't create test user")


class TestGroupName(object):

    def testGroupNames(self):
        """ user: isValidName: reject group names """
        test = u'AdminGroup'
        assert not user.isValidName(test)


class TestIsValidName(object):

    def testNonAlnumCharacters(self):
        """ user: isValidName: reject unicode non alpha numeric characters

        : and , used in acl rules, we might add more characters to the syntax.
        """
        invalid = u'! # $ % ^ & * ( ) = + , : ; " | ~ / \\ \u0000 \u202a'.split()
        base = u'User%sName'
        for c in invalid:
            name = base % c
            assert not user.isValidName(name)

    def testWhitespace(self):
        """ user: isValidName: reject leading, trailing or multiple whitespace """
        cases = (
            u' User Name',
            u'User Name ',
            u'User   Name',
            )
        for test in cases:
            assert not user.isValidName(test)

    def testValid(self):
        """ user: isValidName: accept names in any language, with spaces """
        cases = (
            u'Jürgen Hermann', # German
            u'ניר סופר', # Hebrew
            u'CamelCase', # Good old camel case
            u'가각간갇갈 갉갊감 갬갯걀갼' # Hangul (gibberish)
            )
        for test in cases:
            assert user.isValidName(test)


coverage_modules = ['MoinMoin.user']

