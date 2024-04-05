# Copyright: 2007 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.config.default Tests
"""


import pytest

from flask import current_app as app


class TestPasswordChecker:
    username = "SomeUser"
    tests_builtin = [
        ("", False),  # empty
        ("1966", False),  # too short
        ("asdfghjk", False),  # keyboard sequence
        ("QwertZuiop", False),  # german keyboard sequence, with uppercase
        ("mnbvcx", False),  # reverse keyboard sequence
        ("12345678", False),  # keyboard sequence, too easy
        ("aaaaaaaa", False),  # not enough different chars
        ("BBBaaaddd", False),  # not enough different chars
        (username, False),  # username == password
        (username[1:-1], False),  # password in username
        (f"XXX{username}XXX", False),  # username in password
        ("Moin-2007", True),  # this should be OK
    ]

    def testBuiltinPasswordChecker(self):
        pw_checker = app.cfg.password_checker
        if not pw_checker:
            pytest.skip("password_checker is disabled in the configuration, not testing it")
        else:
            for pw, result in self.tests_builtin:
                pw_error = pw_checker(self.username, pw)
                print(f"{pw!r}: {pw_error}")
                assert result == (pw_error is None)


coverage_modules = ["moin.config.default"]
