# Copyright: 2012-2025 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - cryptographic and random functions.

Features:
- Password hashing with Argon2id
- Generate password-recovery tokens
- Verify password-recovery tokens
- Generate random strings of a given length (for salting)
"""

import hashlib
import hmac
import re
import secrets
import time

from uuid import uuid4

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from moin.constants.keys import HASH_ALGORITHM
from moin.utils import sha512_crypt

from moin import log

logging = log.getLogger(__name__)


def make_uuid():
    return str(uuid4().hex)


UUID_LEN = len(make_uuid())


def random_string(length, allowed_chars=None):
    """
    Generate a random string of the given length consisting of the given characters.

    Uses Python's secrets module for cryptographically secure randomness.

    :param length: Length of the string.
    :param allowed_chars: String of allowed characters.
    :returns: Random string.
    """
    assert allowed_chars is not None
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


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
        # Generate a 32-character URL-safe token (24 bytes = 32 chars in base64)
        key = secrets.token_urlsafe(24)
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
    return hmac.compare_digest(token, expected_token)


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


# password hashing


class PasswordHasher:
    """
    Password hasher with Argon2id support and legacy hash compatibility.

    New passwords are hashed with Argon2id. Legacy sha512_crypt hashes
    are verified and automatically upgraded to Argon2id on successful login.
    """

    # Regex to identify sha512_crypt hashes (from passlib)
    SHA512_CRYPT_PATTERN = re.compile(r"^\$6\$")

    def __init__(self, time_cost=2, memory_cost=102400, parallelism=8, hash_len=16, salt_len=16):
        """
        Initialize the password hasher.

        :param time_cost: Number of iterations (default: 2)
        :param memory_cost: Memory usage in KiB (default: 100 MiB)
        :param parallelism: Number of parallel threads (default: 8)
        :param hash_len: Length of the hash in bytes (default: 16)
        :param salt_len: Length of the salt in bytes (default: 16)
        """
        self.argon2_hasher = Argon2PasswordHasher(
            time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism, hash_len=hash_len, salt_len=salt_len
        )

    def hash(self, password):
        """
        Hash a password using Argon2id.

        :param password: Plain text password (str)
        :returns: Argon2id hash (str)
        """
        return self.argon2_hasher.hash(password)

    def verify(self, password_hash, password):
        """
        Verify a password against a hash.

        Supports both Argon2id hashes and legacy sha512_crypt hashes.

        :param password_hash: The stored password hash (str)
        :param password: The password to verify (str)
        :returns: True if password matches, False otherwise
        """
        if not password_hash or not password:
            return False

        # Check if it's an Argon2 hash
        if password_hash.startswith("$argon2"):
            try:
                self.argon2_hasher.verify(password_hash, password)
                return True
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                return False

        # Check if it's a legacy sha512_crypt hash
        elif self.SHA512_CRYPT_PATTERN.match(password_hash):
            return self._verify_sha512_crypt(password_hash, password)

        else:
            logging.warning(f"Unknown password hash format: {password_hash[:20]}...")
            return False

    def verify_and_update(self, password, password_hash):
        """
        Verify a password and return whether it needs rehashing.

        This is compatible with passlib's CryptContext.verify_and_update() API.

        :param password: The password to verify (str)
        :param password_hash: The stored password hash (str)
        :returns: Tuple of (verified: bool, new_hash: str or None)
                 new_hash is None if no update needed, otherwise contains new Argon2 hash
        """
        if not self.verify(password_hash, password):
            return False, None

        # If it's already Argon2 and doesn't need rehashing, return None
        if password_hash.startswith("$argon2"):
            try:
                if self.argon2_hasher.check_needs_rehash(password_hash):
                    return True, self.hash(password)
                else:
                    return True, None
            except (VerificationError, InvalidHashError):
                # If we can't check, assume it needs rehashing
                return True, self.hash(password)

        # Legacy hash - upgrade to Argon2
        return True, self.hash(password)

    def _verify_sha512_crypt(self, password_hash, password):
        """
        Verify a password against a sha512_crypt hash.

        :param password_hash: sha512_crypt hash (str)
        :param password: Password to verify (str)
        :returns: True if password matches, False otherwise
        """
        try:
            return sha512_crypt.verify(password, password_hash)
        except Exception as err:
            logging.error(f"Error verifying sha512_crypt hash: {err}")
            return False
