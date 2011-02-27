"""
    MoinMoin - search expression object representation

    This module defines the possible search terms for a query to the
    storage backend. This is used, for example, to implement searching,
    page lists etc.

    Note that some backends can optimise some of the search terms, for
    example a backend that has indexed various metadata keys can optimise
    easy expressions containing ItemMetaDataMatch terms. This is only allowed
    for classes documented as being 'final' which hence also means that
    their _evaluate function may not be overridden by descendent classes.

    For example, that metadata backend could test if the expression is an
    ItemMetaDataMatch expression, and if so, simply return the appropriate
    index; or if it is an AND() expression build the page list from the
    index, remove the ItemMetaDataMatch instance from the AND list and match
    the resulting expression only for pages in that list. Etc.

    TODO: Should we write some generic code for picking apart expressions
          like that?

    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import re

from MoinMoin.storage.error import NoSuchRevisionError

# Base classes

class Term(object):
    """
    Base class for search terms.
    """
    # relative cost of this search term
    _cost = 0

    def __init__(self):
        pass

    def evaluate(self, item):
        """
        Evaluate this term and return True or False if the
        item identified by the parameters matches.

        @param item: the item
        """
        assert hasattr(self, '_result')

        if self._result is None:
            self._result = self._evaluate(item)

        return self._result

    def _evaluate(self, item):
        """
        Implements the actual evaluation
        """
        raise NotImplementedError()

    def prepare(self):
        """
        Prepare this search term to make it ready for testing.
        Must be called before each outermost-level evaluate.
        """
        self._result = None

    def copy(self):
        """
        Make a copy of this search term.
        """
        return self.__class__()

class UnaryTerm(Term):
    """
    Base class for search terms that has a single contained
    search term, e.g. NOT.
    """
    def __init__(self, term):
        Term.__init__(self)
        assert isinstance(term, Term)
        self.term = term

    def prepare(self):
        Term.prepare(self)
        self.term.prepare()
        self._cost = self.term._cost

    def __repr__(self):
        return u'<%s(%r)>' % (self.__class__.__name__, self.term)

    def copy(self):
        return self.__class__(self.term.copy())

class ListTerm(Term):
    """
    Base class for search terms that contain multiple other
    search terms, e.g. AND.
    """
    def __init__(self, *terms):
        Term.__init__(self)
        for e in terms:
            assert isinstance(e, Term)
        self.terms = list(terms)

    def prepare(self):
        Term.prepare(self)
        # the sum of all costs is a bit of a worst-case cost...
        self._cost = 0
        for e in self.terms:
            e.prepare()
            self._cost += e._cost
        self.terms.sort(cmp=lambda x, y: cmp(x._cost, y._cost))

    def remove(self, subterm):
        self.terms.remove(subterm)

    def add(self, subterm):
        self.terms.append(subterm)

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__,
                              ', '.join([repr(t) for t in self.terms]))

    def copy(self):
        terms = [t.copy() for t in self.terms]
        return self.__class__(*terms)

# Logical expression classes

class AND(ListTerm):
    """
    AND connection between multiple terms. Final.
    """
    def _evaluate(self, item):
        for e in self.terms:
            if not e.evaluate(item):
                return False
        return True

class OR(ListTerm):
    """
    OR connection between multiple terms. Final.
    """
    def _evaluate(self, item):
        for e in self.terms:
            if e.evaluate(item):
                return True
        return False

class NOT(UnaryTerm):
    """
    Inversion of a single term. Final.
    """
    def _evaluate(self, item):
        return not self.term.evaluate(item)

class XOR(ListTerm):
    """
    XOR connection between multiple terms, i.e. exactly
    one must be True. Final.
    """
    def _evaluate(self, item):
        count = 0
        for e in self.terms:
            if e.evaluate(item):
                count += 1
        return count == 1

class _BOOL(Term):
    _cost = 0
    def __init__(self, val):
        self._val = val

    def prepare(self):
        self._result = self._val

    def __repr__(self):
        return '<%s>' % str(self._val).upper()

    def copy(self):
        return self

TRUE = _BOOL(True)
FALSE = _BOOL(False)

def BOOL(b):
    if b:
        return TRUE
    return FALSE

# Actual Moin search terms

class TextRE(Term):
    """
    Regular expression full text match, use as last resort.
    """
    _cost = 1000 # almost prohibitive
    def __init__(self, needle_re):
        Term.__init__(self)
        assert hasattr(needle_re, 'search')
        self._needle_re = needle_re

    def _evaluate(self, item):
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            return False
        data = rev.read()
        return not (not self._needle_re.search(data))

    def __repr__(self):
        return u'<term.TextRE(...)>'

    def copy(self):
        return TextRE(self._needle_re)

class Text(TextRE):
    """
    Full text match including middle of words and over word
    boundaries. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle), flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Text(%s, %s)>' % (self.needle, self.case_sensitive)

    def copy(self):
        return Text(self.needle, self.case_sensitive)

class Word(TextRE):
    """
    Full text match finding exact words. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile('\\b' + re.escape(needle) + '\\b', flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Word(%s, %s)>' % (self.needle, self.case_sensitive)

    def copy(self):
        return Word(self.needle, self.case_sensitive)

class WordStart(TextRE):
    """
    Full text match finding the start of a word. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile('\\b' + re.escape(needle), flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.WordStart(%s, %s)>' % (self.needle, self.case_sensitive)

    def copy(self):
        return WordStart(self.needle, self.case_sensitive)

class WordEnd(TextRE):
    """
    Full text match finding the end of a word. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle) + '\\b', flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.WordEnd(%s, %s)>' % (self.needle, self.case_sensitive)

    def copy(self):
        return WordEnd(self.needle, self.case_sensitive)

class NameRE(Term):
    """
    Matches the item's name with a given regular expression.
    """
    _cost = 10 # one of the cheapest
    def __init__(self, needle_re):
        Term.__init__(self)
        assert hasattr(needle_re, 'search')
        self._needle_re = needle_re

    def _evaluate(self, item):
        return not (not self._needle_re.search(item.name))

    def __repr__(self):
        return u'<term.NameRE(...)>'

    def copy(self):
        return NameRE(self._needle_re)

class Name(NameRE):
    """
    Item name match, given needle must occur in item's name. Final.
    """
    def __init__(self, needle, case_sensitive):
        assert isinstance(needle, unicode)
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle), flags)
        NameRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Name(%s, %s)>' % (self.needle, self.case_sensitive)

    def copy(self):
        return Name(self.needle, self.case_sensitive)

class NameFn(Term):
    """
    Arbitrary item name matching function.
    """
    def __init__(self, fn):
        Term.__init__(self)
        assert callable(fn)
        self._fn = fn

    def _evaluate(self, item):
        return not (not self._fn(item.name))

    def __repr__(self):
        return u'<term.NameFn(%r)>' % (self._fn, )

    def copy(self):
        return NameFn(self._fn)

class ItemMetaDataMatch(Term):
    """
    Matches a metadata key/value pair of an item, requires
    existence of the metadata key. Final.
    """
    _cost = 100 # fairly expensive but way cheaper than text
    def __init__(self, key, val):
        Term.__init__(self)
        self.key = key
        self.val = val

    def _evaluate(self, item):
        return self.key in item and item[self.key] == self.val

    def __repr__(self):
        return u'<%s(%s: %s)>' % (self.__class__.__name__, self.key, self.val)

    def copy(self):
        return ItemMetaDataMatch(self.key, self.val)

class ItemHasMetaDataValue(Term):
    """
    Match when the metadata value for a given key contains the given
    value (when the item's metadata value is a dict or list), requires
    existence of the metadata key. Final.
    """
    _cost = 100 # fairly expensive but way cheaper than text
    def __init__(self, key, val):
        Term.__init__(self)
        self.key = key
        self.val = val

    def _evaluate(self, item):
        return self.key in item and self.val in item[self.key]

    def __repr__(self):
        return u'<%s(%s: %s)>' % (self.__class__.__name__, self.key, self.val)

    def copy(self):
        return ItemHasMetaDataValue(self.key, self.val)

class ItemHasMetaDataKey(Term):
    """
    Requires existence of the metadata key. Final.
    """
    _cost = 90 # possibly cheaper than ItemMetaDataMatch
    def __init__(self, key):
        Term.__init__(self)
        self.key = key

    def _evaluate(self, item):
        return self.key in item

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__, self.key)

    def copy(self):
        return ItemHasMetaDataKey(self.key)

class LastRevisionMetaDataMatch(Term):
    """
    Matches a metadata key/value pair of an item, requires
    existence of the metadata key. Final.
    """
    _cost = 100 # fairly expensive but way cheaper than text
    def __init__(self, key, val):
        Term.__init__(self)
        self.key = key
        self.val = val

    def _evaluate(self, item):
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            return False
        return self.key in rev and rev[self.key] == self.val

    def __repr__(self):
        return u'<%s(%s: %s)>' % (self.__class__.__name__, self.key, self.val)

    def copy(self):
        return LastRevisionMetaDataMatch(self.key, self.val)

class LastRevisionHasMetaDataKey(Term):
    """
    Requires existence of the metadata key. Final.
    """
    _cost = 90 # possibly cheaper than LastRevisionMetaDataMatch
    def __init__(self, key):
        Term.__init__(self)
        self.key = key

    def _evaluate(self, item):
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            return False
        return self.key in rev

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__, self.key)

    def copy(self):
        return LastRevisionHasMetaDataKey(self.key)

