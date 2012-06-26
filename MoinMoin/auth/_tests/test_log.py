# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for auth.log
"""

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.auth.log import AuthLog
from flask import g as flaskg
import pytest

class TestAuthLog(object):
    """ Test: TestAuthLog """
    def test_login(self):
        authlog_obj = AuthLog()
        result = authlog_obj.login(flaskg.user)
        assert result.continue_flag
        test_user_obj = result.user_obj
        assert test_user_obj.name == u'anonymous'

    def test_request(self):
        authlog_obj = AuthLog()
        result = authlog_obj.request(flaskg.user)
        test_user, bool_value = result
        assert test_user.name == u'anonymous'
        assert not test_user.valid
        assert bool_value

    def test_logout(self):
        authlog_obj = AuthLog()
        result = authlog_obj.logout(flaskg.user)
        test_user, bool_value = result
        assert test_user.name == u'anonymous'
        assert not test_user.valid
        assert bool_value
