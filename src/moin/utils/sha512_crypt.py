# Copyright: 2025 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Pure Python implementation of sha512_crypt.

This module provides a pure Python implementation of the sha512_crypt password
hashing algorithm as specified in https://www.akkadia.org/drepper/SHA-crypt.txt

No external dependencies required - uses only Python's standard library.
"""

import hashlib
import hmac


def verify(password, hash_string):
    """
    Verify a password against a sha512_crypt hash.

    :param password: Plain text password (str)
    :param hash_string: sha512_crypt hash string (str)
    :returns: True if password matches, False otherwise
    """
    # Parse the hash string
    parts = hash_string.split("$")
    if len(parts) < 4 or parts[1] != "6":
        return False

    # Check for custom rounds
    if parts[2].startswith("rounds="):
        rounds = int(parts[2].split("=")[1])
        salt = parts[3]
        expected_hash = parts[4] if len(parts) > 4 else ""
    else:
        rounds = 5000  # default rounds
        salt = parts[2]
        expected_hash = parts[3] if len(parts) > 3 else ""

    # Compute the hash
    computed_hash = crypt(password, salt, rounds)

    # Constant-time comparison
    return hmac.compare_digest(computed_hash, expected_hash)


def crypt(password, salt, rounds=5000):
    """
    Compute sha512_crypt hash following the specification.

    :param password: Plain text password (str)
    :param salt: Salt string (str)
    :param rounds: Number of rounds (int, default: 5000)
    :returns: Base64-encoded hash (str)
    """
    password_bytes = password.encode("utf-8") if isinstance(password, str) else password
    salt_bytes = salt.encode("utf-8") if isinstance(salt, str) else salt
    salt_bytes = salt_bytes[:16]  # Limit salt to 16 characters

    pw_len = len(password_bytes)
    salt_len = len(salt_bytes)

    # Step 1-3: Compute digest B
    digest_b = hashlib.sha512(password_bytes + salt_bytes + password_bytes).digest()

    # Step 4-8: Start digest A
    digest_a = hashlib.sha512()
    digest_a.update(password_bytes)
    digest_a.update(salt_bytes)

    # Step 9-10: Add digest B
    for i in range(pw_len, 0, -64):
        digest_a.update(digest_b if i > 64 else digest_b[:i])

    # Step 11-12: Process password length
    i = pw_len
    while i > 0:
        if i & 1:
            digest_a.update(digest_b)
        else:
            digest_a.update(password_bytes)
        i >>= 1

    digest_a_result = digest_a.digest()

    # Step 13-15: Compute DP (digest of password)
    digest_dp = hashlib.sha512()
    for _ in range(pw_len):
        digest_dp.update(password_bytes)
    dp = digest_dp.digest()

    # Step 16a: Create P sequence
    p_bytes = b"".join(dp[: pw_len - i] if pw_len - i < 64 else dp for i in range(0, pw_len, 64))

    # Step 16b-18: Compute DS (digest of salt)
    digest_ds = hashlib.sha512()
    for _ in range(16 + digest_a_result[0]):
        digest_ds.update(salt_bytes)
    ds = digest_ds.digest()

    # Step 19: Create S sequence
    s_bytes = b"".join(ds[: salt_len - i] if salt_len - i < 64 else ds for i in range(0, salt_len, 64))

    # Step 20: Repeatedly run hash function
    digest_c = digest_a_result
    for round_num in range(rounds):
        digest = hashlib.sha512()

        if round_num & 1:
            digest.update(p_bytes)
        else:
            digest.update(digest_c)

        if round_num % 3:
            digest.update(s_bytes)

        if round_num % 7:
            digest.update(p_bytes)

        if round_num & 1:
            digest.update(digest_c)
        else:
            digest.update(p_bytes)

        digest_c = digest.digest()

    # Step 21: Encode result using custom base64
    return _b64encode(digest_c)


def _b64encode(digest):
    """
    Encode digest using sha512_crypt's custom base64 alphabet.

    :param digest: 64-byte digest (bytes)
    :returns: Base64-encoded string (str)
    """
    alphabet = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    def b64_from_24bit(b2, b1, b0, n):
        """Encode 3 bytes into n base64 characters."""
        val = (b2 << 16) | (b1 << 8) | b0
        result = ""
        for _ in range(n):
            result += alphabet[val & 0x3F]
            val >>= 6
        return result

    # Encode in the specific order for sha512_crypt
    result = ""
    result += b64_from_24bit(digest[0], digest[21], digest[42], 4)
    result += b64_from_24bit(digest[22], digest[43], digest[1], 4)
    result += b64_from_24bit(digest[44], digest[2], digest[23], 4)
    result += b64_from_24bit(digest[3], digest[24], digest[45], 4)
    result += b64_from_24bit(digest[25], digest[46], digest[4], 4)
    result += b64_from_24bit(digest[47], digest[5], digest[26], 4)
    result += b64_from_24bit(digest[6], digest[27], digest[48], 4)
    result += b64_from_24bit(digest[28], digest[49], digest[7], 4)
    result += b64_from_24bit(digest[50], digest[8], digest[29], 4)
    result += b64_from_24bit(digest[9], digest[30], digest[51], 4)
    result += b64_from_24bit(digest[31], digest[52], digest[10], 4)
    result += b64_from_24bit(digest[53], digest[11], digest[32], 4)
    result += b64_from_24bit(digest[12], digest[33], digest[54], 4)
    result += b64_from_24bit(digest[34], digest[55], digest[13], 4)
    result += b64_from_24bit(digest[56], digest[14], digest[35], 4)
    result += b64_from_24bit(digest[15], digest[36], digest[57], 4)
    result += b64_from_24bit(digest[37], digest[58], digest[16], 4)
    result += b64_from_24bit(digest[59], digest[17], digest[38], 4)
    result += b64_from_24bit(digest[18], digest[39], digest[60], 4)
    result += b64_from_24bit(digest[40], digest[61], digest[19], 4)
    result += b64_from_24bit(digest[62], digest[20], digest[41], 4)
    result += b64_from_24bit(0, 0, digest[63], 2)

    return result
