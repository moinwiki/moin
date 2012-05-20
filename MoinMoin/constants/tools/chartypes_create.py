# Copyright: 2004 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    Build MoinMoin.constants.chartypes with
    UCS-2 character types (upper/lower/digits/spaces).
"""


def main():
    uppercase = []
    lowercase = []
    digits = []
    space = []
    for code in range(1, 65535):
        c = unichr(code)
        str = "\\u{0:04x}".format(code)
        if c.isupper():
            uppercase.append(str)
        elif c.islower():
            lowercase.append(str)
        elif c.isdigit():
            digits.append(str)
        elif c.isspace():
            space.append(str)

    chars_upper = u''.join(uppercase)
    chars_lower = u''.join(lowercase+digits)
    chars_digits = u''.join(digits)
    chars_spaces = u''.join(space)

    print """
chars_upper = u"%(chars_upper)s"

chars_lower = u"%(chars_lower)s"

chars_digits = u"%(chars_digits)s"

chars_spaces = u"%(chars_spaces)s"


""" % locals()

if __name__ == '__main__':
    main()

