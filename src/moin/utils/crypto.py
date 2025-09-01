# Copyright: 2012-2013 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - cryptographic and random functions.

Features:
- Generate password-recovery tokens
- Verify password-recovery tokens
- Generate random strings of a given length (for salting)
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
    Generate a random string of the given length consisting of the given characters.

    Note: this is now just a small wrapper around Passlib's randomness code.

    :param length: Length of the string.
    :param allowed_chars: String of allowed characters.
    :returns: Random string.
    """
    assert allowed_chars is not None
    s = getrandstr(rng, allowed_chars, length)
    return s


# password recovery token


def generate_token(key=None, stamp=None):
    """
    Generate a pair consisting of a secret key and a token.

    You can use this to implement password-recovery functionality by
    calling generate_token(), transmitting the returned token to the
    correct user (e.g., by email), and storing the returned (secret) key
    in the user's profile on the server side.

    After the user receives the token, they return to the wiki, enter their
    user name or email address, and the token they received. Read the (secret)
    key from the user profile and call valid_token(key, token) to verify
    whether the token is valid. If it is valid, consider the user authenticated,
    remove the secret key from their profile, and allow them to reset the password.

    :param key: Recompute a specific token for verification using this key.
    :param stamp: Recompute a specific token for verification using this timestamp.
    :rtype: 2-tuple
    :returns: key, token (both strings)
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
    Check whether a token is valid with respect to the secret key.
    The token must not be older than the timeout (in seconds).

    :param key: The secret key to verify the token.
    :param token: The token to verify.
    :param timeout: Timeout in seconds; set to None to ignore the timeout.
    :rtype: bool
    :returns: True if the token is valid and not timed out; otherwise False.
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
    Calculate a cache key (ASCII only).

    Important key properties:

    * The key must be different for different kw.
    * The key is pure ASCII.

    :param kw: Keys/values to compute the cache key from.
    """
    return hashlib.md5(repr(kw).encode(), usedforsecurity=False).hexdigest()


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
