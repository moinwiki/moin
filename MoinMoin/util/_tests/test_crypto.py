# -*- coding: utf-8 -*-
# Copyright: 2011 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.crypto Tests
"""


import py

from MoinMoin.util import crypto


class TestRandom(object):
    """ crypto: random tests """

    def testRandomString(self):
        """ util.random_string: test randomness and length """
        length = 8
        result1 = crypto.random_string(length)
        result2 = crypto.random_string(length)
        assert result1 != result2, ('Expected different random strings, but got "%(result1)s" and "%(result2)s"') % locals()

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


coverage_modules = ['MoinMoin.util.crypto']

