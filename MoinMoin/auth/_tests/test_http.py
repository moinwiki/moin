# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for auth.http
"""

from flask import g as flaskg
from flask import request

from MoinMoin.user import create_user
from MoinMoin.auth.http import HTTPAuthMoin
import pytest

class TestHTTPAuthMoin(object):
    """ Test: HTTPAuthMoin """
    class Auth:
        def __init__(self):
            self.username = 'ValidUser'
            self.password = 'test_pass'

    def setup_method(self, metod):
        flaskg.user.auth_method = 'http'
        request.authorization = self.Auth()

    def teardown_method(self, method):
        flaskg.user.auth_method = 'invalid'
        request.authorization = None

    def test_request(self):
        # create a new user
        create_user(u'ValidUser', 'test_pass', 'test_email@moinmoin')
        httpauthmoin_obj = HTTPAuthMoin()
        test_user, bool_val = httpauthmoin_obj.request(flaskg.user)
        assert test_user.valid
        assert test_user.name == u'ValidUser'
        assert bool_val

        # when auth_method is not 'http'
        flaskg.user.auth_method = 'invalid'
        test_user, bool_val = httpauthmoin_obj.request(flaskg.user)
        assert not test_user.valid
        assert test_user.name == u'anonymous'

