# Copyright: 2004 Juergen Hermann, Thomas Waldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Utility Functions
    General helper functions that are not directly wiki related.
"""


import re, random

# do the pickle magic once here, so we can just import from here:
# cPickle can encode normal and Unicode strings
# see http://docs.python.org/lib/node66.html
try:
    import cPickle as pickle
except ImportError:
    import pickle

# Set pickle protocol, see http://docs.python.org/lib/node64.html
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL


#############################################################################
### XML helper functions
#############################################################################

g_xmlIllegalCharPattern = re.compile('[\x01-\x08\x0B-\x0D\x0E-\x1F\x80-\xFF]')
g_undoUtf8Pattern = re.compile('\xC2([^\xC2])')
g_cdataCharPattern = re.compile('[&<\'\"]')
g_textCharPattern = re.compile('[&<]')
g_charToEntity = {
    '&': '&amp;',
    '<': '&lt;',
    "'": '&apos;',
    '"': '&quot;'
}

def TranslateCDATA(text):
    """
        Convert a string to a CDATA-encoded one
        Copyright (c) 1999-2000 FourThought, http://4suite.com/4DOM
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_cdataCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: '&#x%02X;' % ord(m.group()), new_string)
    return new_string

def TranslateText(text):
    """
        Convert a string to a PCDATA-encoded one (do minimal encoding)
        Copyright (c) 1999-2000 FourThought, http://4suite.com/4DOM
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_textCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: '&#x%02X;' % ord(m.group()), new_string)
    return new_string


#############################################################################
### Misc
#############################################################################

def rangelist(numbers):
    """ Convert a list of integers to a range string in the form
        '1,2-5,7'.
    """
    numbers = numbers[:]
    numbers.sort()
    numbers.append(999999)
    pattern = ','
    for i in range(len(numbers)-1):
        if pattern[-1] == ',':
            pattern = pattern + str(numbers[i])
            if numbers[i] + 1 == numbers[i+1]:
                pattern = pattern + '-'
            else:
                pattern = pattern + ','
        elif numbers[i] + 1 != numbers[i+1]:
            pattern = pattern + str(numbers[i]) + ','

    if pattern[-1] in ',-':
        return pattern[1:-1]
    return pattern[1:]


def random_string(length, allowed_chars=None):
    """ Generate a random string with given length consisting
        of the given characters.

        :param length: length of the string
        :param allowed_chars: string with allowed characters or None
                              to indicate all 256 byte values should be used
        :returns: random string
    """
    if allowed_chars is None:
        return ''.join([chr(random.randint(0, 255)) for dummy in xrange(length)])

    return ''.join([random.choice(allowed_chars) for dummy in xrange(length)])
