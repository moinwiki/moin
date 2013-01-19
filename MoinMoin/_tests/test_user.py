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


class TestSimple(object):
    def test_create_retrieve(self):
        name = u"foo"
        password = u"barbaz4711"
        email = u"foo@example.org"
        # nonexisting user
        u = user.User(name=name, password=password)
        assert u.name == name
        assert not u.valid
        assert not u.exists()
        # create a user
        ret = user.create_user(name, password, email, validate=False)
        assert ret is None, "create_user returned: {0}".format(ret)
        # existing user
        u = user.User(name=name, password=password)
        assert u.name == name
        assert u.email == email
        assert u.valid
        assert u.exists()


class TestLoginWithPassword(object):
    """user: login tests"""

    def setup_method(self, method):
        # Save original user
        self.saved_user = flaskg.user

        # Create anon user for the tests
        flaskg.user = user.User()

    def teardown_method(self, method):
        """ Run after each test

        Remove user and reset user listing cache.
        """
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

    def test_login(self):
        """
        Create user with some password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        password = '12345'
        salt = 'salt'
        pw_hash = ''
        self.createUser(name, pw_hash, True)

        # Try to "login"
        theuser = user.User(name=name, password=password)
        assert theuser.valid

    def testSubscriptionSubscribedPage(self):
        """ user: tests is_subscribed_to  """
        pagename = u'HelpMiscellaneous'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert theUser.is_subscribed_to([pagename]) # list(!) of pages to check

    def testSubscriptionSubPage(self):
        """ user: tests is_subscribed_to on a subpage """
        pagename = u'HelpMiscellaneous'
        testPagename = u'HelpMiscellaneous/FrequentlyAskedQuestions'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert not theUser.is_subscribed_to([testPagename]) # list(!) of pages to check

    # Bookmarks -------------------------------------------------------

    def test_bookmark(self):
        name = u'Test_User_bookmark'
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
        pagename = u'Test_page_quicklink'
        name = u'Test_User_quicklink'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # no quick links exist yet
        result_before = theUser.quicklinks
        assert result_before == []

        result = theUser.is_quicklinked_to([pagename])
        assert not result

        # add quicklink
        theUser.quicklink(u'Test_page_added')
        result_on_addition = theUser.quicklinks
        expected = [u'MoinTest:Test_page_added']
        assert result_on_addition == expected

        # remove quicklink
        theUser.quickunlink(u'Test_page_added')
        result_on_removal = theUser.quicklinks
        expected = []
        assert result_on_removal == expected

    # Trail -----------------------------------------------------------

    def test_trail(self):
        pagename = u'Test_page_trail'
        name = u'Test_User_trail'
        password = name
        self.createUser(name, password)
        theUser = user.User(name=name, password=password)

        # no item name added to trail
        result = theUser.get_trail()
        expected = []
        assert result == expected

        # item name added to trail
        theUser.add_trail(u'item_added')
        theUser = user.User(name=name, password=password)
        result = theUser.get_trail()
        expected = [u'MoinTest:item_added']
        assert result == expected

    # Sessions -------------------------------------------------------

    def test_sessions(self):
        name = u'Test_User_sessions'
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

    def createUser(self, name, password, pwencoded=False, email=None, validate=False):
        ret = user.create_user(name, password, email, validate=validate, is_encrypted=pwencoded)
        assert ret is None, "create_user returned: {0}".format(ret)


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
        base = u'User{0}Name'
        for c in invalid:
            name = base.format(c)
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
