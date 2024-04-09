# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for auth.__init__
"""

from flask import g as flaskg

from moin._tests import wikiconfig
from moin.constants.misc import ANON
from moin.auth import GivenAuth, handle_login, get_multistage_continuation_url
from moin.user import create_user

import pytest


class TestConfiguredGivenAuth:
    """Test: configured GivenAuth"""

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            auth = [GivenAuth(user_name="JoeDoe", autocreate=True)]

        return Config

    def test(self):
        assert flaskg.user.name == ["JoeDoe"]


class TestGivenAuth:
    """Test: GivenAuth"""

    def test_decode_username(self):
        givenauth_obj = GivenAuth()
        result1 = givenauth_obj.decode_username("test_name")
        assert result1 == "test_name"
        result2 = givenauth_obj.decode_username(123.45)
        assert result2 == 123.45

    def test_transform_username(self):
        givenauth_obj = GivenAuth()
        givenauth_obj.strip_maildomain = True
        givenauth_obj.strip_windomain = True
        givenauth_obj.titlecase = True
        givenauth_obj.remove_blanks = True
        result = givenauth_obj.transform_username("testDomain\\test name@moinmoin.org")
        assert result == "TestName"

    def test_request(self):
        givenauth_obj = GivenAuth()
        flaskg.user.auth_method = "given"
        givenauth_obj.user_name = "testDomain\\test_user@moinmoin.org"
        givenauth_obj.strip_maildomain = True
        givenauth_obj.strip_windomain = True
        givenauth_obj.titlecase = True
        givenauth_obj.remove_blanks = True
        create_user("Test_User", "test_pass", "test@moinmoin.org")
        test_user, bool_value = givenauth_obj.request(flaskg.user)
        assert test_user.valid
        assert test_user.name == ["Test_User"]


def test_handle_login():
    # no messages in the beginning
    assert not flaskg._login_messages
    test_user1 = handle_login(flaskg.user, login_username="test_user", login_password="test_password", stage="moin")
    test_login_message = ["Invalid username or password."]
    assert flaskg._login_messages == test_login_message
    assert test_user1.name0 == ANON
    assert not test_user1.valid
    # pop the message
    flaskg._login_messages.pop()
    # try with a valid user
    givenauth_obj = GivenAuth()
    flaskg.user.auth_method = "given"
    givenauth_obj.user_name = "Test_User"
    create_user("Test_User", "test_pass", "test@moinmoin.org")
    test_user, bool_value = givenauth_obj.request(flaskg.user)
    test_user2 = handle_login(test_user, login_username="Test_User", login_password="test_pass", stage="moin")
    assert not flaskg._login_messages
    assert test_user2.name == ["Test_User"]
    assert test_user2.valid


def test_get_multistage_continuation_url():
    test_url = get_multistage_continuation_url(
        "test_auth_name", extra_fields={"password": "test_pass", "test_key": "test_value"}
    )
    assert "test_key=test_value" in test_url
    assert "password=test_pass" in test_url
    assert "stage=test_auth_name" in test_url
    assert "login_submit=1" in test_url
