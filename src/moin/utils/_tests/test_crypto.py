# Copyright: 2011-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.crypto Tests
"""


from moin.utils import crypto


class TestRandom:
    """crypto: random tests"""

    def testRandomString(self):
        """utils.random_string: test randomness and length"""
        length = 8
        chars = "abcdefghijklmnopqrstuvwxyz"
        result1 = crypto.random_string(length, chars)
        result2 = crypto.random_string(length, chars)
        assert result1 != result2, (
            'Expected different random strings, but got "%(result1)s" and "%(result2)s"' % locals()
        )

        result_string = crypto.random_string(length, chars)
        assert isinstance(result_string, str), "Expected a string value, but got " + str(type(result_string))

        result = len(crypto.random_string(length, chars))
        expected = length
        assert result == expected, 'Expected length "%(expected)s" but got "%(result)s"' % locals()


class TestToken:
    """tests for the generated tokens"""

    def test_validtoken(self):
        """validate the token"""
        test_key, test_token = crypto.generate_token(key="MoinMoin")  # having some key value
        result = crypto.valid_token(test_key, test_token)
        assert result

        test_key, test_token = crypto.generate_token()  # key value is none
        result = crypto.valid_token(test_key, test_token)
        assert result

        test_parts = test_token.split("-")
        test_parts[0] = "not_valid"
        # changed value of the first part, should not be string
        test_token_changed = "-".join(test_parts)
        result = crypto.valid_token(test_key, test_token_changed)
        assert not result

        test_key, test_token = "MoinMoin", "incorrect_token"
        result = crypto.valid_token(test_key, test_token)
        assert not result


class TestCacheKey:
    """tests for cache key generation"""

    def test_cache_key(self):
        """The key must be different for different <kw>"""
        test_kw1 = {"MoinMoin": "value1"}
        result1 = crypto.cache_key(**test_kw1)
        test_kw2 = {"Moin2": "value2"}
        result2 = crypto.cache_key(**test_kw2)
        assert result1 != result2, "Expected different keys for different <kw> but got the same"


coverage_modules = ["moin.utils.crypto"]
