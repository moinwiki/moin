# Copyright: 2012-2013 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Cryptographic and random functions

Features:

- generate password recovery tokens
- verify password recovery tokens
- generate random strings of given length (for salting)
"""

from __future__ import absolute_import, division

import hashlib
import hmac
import time

from uuid import uuid4

make_uuid = lambda: unicode(uuid4().hex)
UUID_LEN = len(make_uuid())

from passlib.utils import rng, getrandstr, getrandbytes, consteq, generate_password


def random_string(length, allowed_chars=None):
    """
    Generate a random string with given length consisting of the given characters.

    Note: this is now just a little wrapper around passlib's randomness code.

    :param length: length of the string
    :param allowed_chars: string with allowed characters or None
                          to indicate all 256 byte values should be used
    :returns: random string
    """
    if allowed_chars is None:
        s = getrandbytes(rng, length)
    else:
        s = getrandstr(rng, allowed_chars, length)
    return s


# password recovery token

def generate_token(key=None, stamp=None):
    """
    generate a pair of a secret key and a crypto token.

    you can use this to implement a password recovery functionality by
    calling generate_token() and transmitting the returned token to the
    (correct) user (e.g. by email) and storing the returned (secret) key
    into the user's profile on the server side.

    after the user received the token, he returns to the wiki, gives his
    user name or email address and the token he received. read the (secret)
    key from the user profile and call valid_token(key, token) to verify
    if the token is valid. if it is, consider the user authenticated, remove
    the secret key from his profile and let him reset his password.

    :param key: give it to recompute some specific token for verification
    :param stamp: give it to recompute some specific token for verification
    :rtype: 2-tuple
    :returns: key, token (both unicode)
    """
    if key is None:
        key = generate_password(size=32)
    if stamp is None:
        stamp = int(time.time())
    h = hmac.new(str(key), str(stamp), digestmod=hashlib.sha256).hexdigest()
    token = u"{0}-{1}".format(stamp, h)
    return unicode(key), token


def valid_token(key, token, timeout=2 * 60 * 60):
    """
    check if token is valid with respect to the secret key,
    the token must not be older than timeout seconds.

    :param key: give the secret key to verify the token
    :param token: the token to verify
    :param timeout: timeout seconds, set to None to ignore timeout
    :rtype: bool
    :returns: token is valid and not timed out
    """
    parts = token.split('-')
    if len(parts) != 2:
        return False
    try:
        stamp = int(parts[0])
    except ValueError:
        return False
    if timeout and stamp + timeout < time.time():
        return False
    expected_token = generate_token(key, stamp)[1]
    return consteq(token, expected_token)


# miscellaneous

def cache_key(**kw):
    """
    Calculate a cache key (ascii only)

    Important key properties:

    * The key must be different for different <kw>.
    * Key is pure ascii

    :param kw: keys/values to compute cache key from
    """
    return hashlib.md5(repr(kw)).hexdigest()
