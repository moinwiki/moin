# Copyright: 2004 Juergen Hermann, Thomas Waldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Utility Functions
    General helper functions that are not directly wiki related.
"""


import re

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
# XML helper functions
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
# Misc
#############################################################################

def rangelist(numbers):
    """ Convert a list of integers to a range string in the form
        '1,2-5,7'.
    """
    numbers = sorted(numbers[:])
    numbers.append(999999)
    pattern = ','
    for i in range(len(numbers) - 1):
        if pattern[-1] == ',':
            pattern += str(numbers[i])
            if numbers[i] + 1 == numbers[i + 1]:
                pattern += '-'
            else:
                pattern += ','
        elif numbers[i] + 1 != numbers[i + 1]:
            pattern = pattern + str(numbers[i]) + ','

    if pattern[-1] in ',-':
        return pattern[1:-1]
    return pattern[1:]


def getPageContent(results, offset, results_per_page):
    """
    Selects the content to show on a single page

    :param results: the whole result, from which results for one page will be selected (generally a generator
           but could be a list also),
    :param offset: after skipping how many results, the selection of results for that page will be done (int),
    :param results_per_page: number of results to be shown on a single page (int)

    :rtype: tuple
    :returns: selected_result (list),
              offset for next page (If 0 then no next page),
              offset for previous page (If less than 0, then no previous page)
    """
    count = 0
    maxcount = offset + results_per_page
    nextPage = False
    selected_result = []
    for result in results:
        if count < offset:
            count += 1
        elif results_per_page and count == maxcount:
            nextPage = True
            break
        else:
            selected_result.append(result)
            count += 1
    if not nextPage:
        count = 0
    if results_per_page and offset:
        previous_offset = max(offset - results_per_page, 0)
    else:
        previous_offset = -1
    next_offset = count
    return selected_result, next_offset, previous_offset
