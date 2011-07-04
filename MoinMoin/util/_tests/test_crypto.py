# -*- coding: utf-8 -*-
# Copyright: 2011 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.crypto Tests
"""


import pytest
from MoinMoin.util import crypto


class TestRandom(object):
    """ crypto: random tests """

    def testRandomString(self):
        """ util.random_string: test randomness and length """
        length = 8
        result1 = crypto.random_string(length)
        result2 = crypto.random_string(length)
        assert result1 != result2, ('Expected different random strings, but got "%(result1)s" and "%(result2)s"') % locals()

        result_string = crypto.random_string(length)
        assert isinstance(result_string, str), ('Expected an string value, but got ' + str(type(result_string)))

        result = len(crypto.random_string(length))
        expected = length
        assert result == expected, ('Expected length "%(expected)s" but got "%(result)s"') % locals()


class TestEncodePassword(object):
    """crypto: encode passwords tests"""

    def testAscii(self):
        """user: encode ascii password"""
        # u'MoinMoin' and 'MoinMoin' should be encoded to same result
        expected = "{SSHA256}n0JB8FCTQCpQeg0bmdgvTGwPKvxm8fVNjSRD+JGNs50xMjM0NQ=="

        result = crypto.crypt_password("MoinMoin", salt='12345')
        assert result == expected
        result = crypto.crypt_password(u"MoinMoin", salt='12345')
        assert result == expected

    def testUnicode(self):
        """ user: encode unicode password """
        result = crypto.crypt_password(u'סיסמה סודית בהחלט', salt='12345') # Hebrew
        expected = "{SSHA256}pdYvYv+4Vph259sv/HAm7zpZTv4sBKX9ITOX/m00HMsxMjM0NQ=="
        assert result == expected
    
    def testupgradepassword(self):
        """ return new password hash with better hash """
        result = crypto.upgrade_password(u'MoinMoin', "junk_hash")
        assert result.startswith('{SSHA256}')

    def testvalidpassword(self):
        """ validate user password """
        hash_val = crypto.crypt_password(u"MoinMoin", salt='12345')
        result = crypto.valid_password(u'MoinMoin', hash_val)
        assert result
        with pytest.raises(ValueError):
            invlid_result = crypto.valid_password("MoinMoin", '{junk_value}')
            

class TestToken(object):
    """ tests for the generated tokens """

    def testvalidtoken(self):
        """ validate the token """
        test_key, test_token = crypto.generate_token(key='MoinMoin') # having some key value
        result = crypto.valid_token(test_key, test_token)
        assert result
        
        test_key, test_token = crypto.generate_token() # key value is none
        result = crypto.valid_token(test_key, test_token)
        assert result
        
        test_parts = test_token.split('-')
        test_parts[0] = 'not_valid'
        # changed value of the first part, should not be string
        test_token_changed = '-'.join(test_parts)
        result = crypto.valid_token(test_key, test_token_changed)
        assert result == False

        test_key, test_token = 'MoinMoin', 'incorrect_token'
        result = crypto.valid_token(test_key, test_token)
        assert result == False

    def testcache_key(self):
        """ The key must be different for different <kw> """
        test_kw1 = {'MoinMoin': 'value1'}
        result1 = crypto.cache_key(**test_kw1)
        test_kw2 = {'Moin2' : 'value2'}
        result2 = crypto.cache_key(**test_kw2)
        assert result1 != result2, ("Expected different keys for different <kw> but got the same")
           
coverage_modules = ['MoinMoin.util.crypto']

