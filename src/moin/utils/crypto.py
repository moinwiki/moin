# Copyright: 2012-2013 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Cryptographic and random functions

Features:

- generate password recovery tokens
- verify password recovery tokens
- generate random strings of given length (for salting)
"""

import hashlib
import hmac
import time

from uuid import uuid4

from passlib.utils import rng, getrandstr, consteq
from passlib.pwd import genword

from moin.constants.keys import HASH_ALGORITHM


def make_uuid():
    return str(uuid4().hex)


UUID_LEN = len(make_uuid())


def random_string(length, allowed_chars=None):
    """
    Generate a random string with given length consisting of the given characters.

    Note: this is now just a little wrapper around passlib's randomness code.

    :param length: length of the str
    :param allowed_chars: str with allowed characters
    :returns: random string
    """
    assert allowed_chars is not None
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
        key = genword(length=32)
    if stamp is None:
        stamp = int(time.time())
    key_encoded = key if isinstance(key, bytes) else key.encode()
    stamp_encoded = str(stamp).encode()
    h = hmac.new(key_encoded, stamp_encoded, digestmod=hashlib.sha256).hexdigest()
    token = f"{stamp}-{h}"
    return str(key), token


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
    parts = token.split("-")
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
    return hashlib.md5(repr(kw).encode()).hexdigest()


def hash_hexdigest(content, bufsize=4096):
    size = 0
    hash = hashlib.new(HASH_ALGORITHM)
    if hasattr(content, "read"):
        while True:
            buf = content.read(bufsize)
            hash.update(buf)
            size += len(buf)
            if not buf:
                break
    elif isinstance(content, bytes):
        hash.update(content)
        size = len(content)
    else:
        raise ValueError(f"unsupported content object: {content!r}")
    return size, HASH_ALGORITHM, str(hash.hexdigest())
