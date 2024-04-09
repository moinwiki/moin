# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for auth.http
"""

from flask import g as flaskg
from flask import request as flask_request

from moin.user import create_user
from moin.auth.http import HTTPAuthMoin
from moin.constants.misc import ANON

import pytest


class TestHTTPAuthMoin:
    """Test: HTTPAuthMoin"""

    @pytest.fixture(autouse=True)
    def custom_setup(self):
        class Auth:
            def __init__(self):
                self.username = "ValidUser"
                self.password = "test_pass"

        flaskg.user.auth_method = "http"
        flask_request.authorization = Auth()

        yield

        flaskg.user.auth_method = "invalid"
        flask_request.authorization = None

    def test_request(self):
        # create a new user
        create_user("ValidUser", "test_pass", "test_email@moinmoin")
        httpauthmoin_obj = HTTPAuthMoin()
        test_user, bool_val = httpauthmoin_obj.request(flaskg.user)
        assert test_user.valid
        assert test_user.name == ["ValidUser"]
        assert bool_val

        # when auth_method is not 'http'
        flaskg.user.auth_method = "invalid"
        test_user, bool_val = httpauthmoin_obj.request(flaskg.user)
        assert not test_user.valid
        assert test_user.name0 == ANON
