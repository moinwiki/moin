# Copyright: 2004 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    Build moin.constants.chartypes with
    UCS-2 character types (upper/lower/digits/spaces).
"""


def main():
    uppercase = []
    lowercase = []
    digits = []
    space = []
    for code in range(1, 65535):
        c = chr(code)
        string = f"\\u{code:04x}"
        if c.isupper():
            uppercase.append(string)
        elif c.islower():
            lowercase.append(string)
        elif c.isdigit():
            digits.append(string)
        elif c.isspace():
            space.append(string)

    chars_upper = "".join(uppercase)
    chars_lower = "".join(lowercase + digits)
    chars_digits = "".join(digits)
    chars_spaces = "".join(space)

    print(
        """
CHARS_UPPER = "%(chars_upper)s"

CHARS_LOWER = "%(chars_lower)s"

CHARS_DIGITS = "%(chars_digits)s"

CHARS_SPACES = "%(chars_spaces)s"


"""
        % locals()
    )


if __name__ == "__main__":
    main()
