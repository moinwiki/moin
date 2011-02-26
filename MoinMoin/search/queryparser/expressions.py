"""
    MoinMoin - search query expressions

    @copyright: 2005 MoinMoin:FlorianFesti,
                2005 MoinMoin:NirSoffer,
                2005 MoinMoin:AlexanderSchremmer,
                2006-2008 MoinMoin:ThomasWaldmann,
                2006 MoinMoin:FranzPletz,
                2009 MoinMoin:DmitrijsMilajevs
    @license: GNU GPL, see COPYING for details
"""

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from MoinMoin import config, wikiutil
from MoinMoin.search.results import Match, TitleMatch, TextMatch


class BaseExpression(object):
    """ Base class for all search terms """

    # costs is estimated time to calculate this term.
    # Number is relative to other terms and has no real unit.
    # It allows to do the fast searches first.
    costs = 0
    _tag = ""

    def __init__(self, pattern, use_re=False, case=False):
        """ Init a text search

        @param pattern: pattern to search for, ascii string or unicode
        @param use_re: treat pattern as re of plain text, bool
        @param case: do case sensitive search, bool
        """
        self._pattern = unicode(pattern)
        self.negated = 0
        self.use_re = use_re
        self.case = case

        if use_re:
            self._tag += 're:'
        if case:
            self._tag += 'case:'

        self.pattern, self.search_re = self._build_re(self._pattern, use_re=use_re, case=case)

    def __str__(self):
        return unicode(self).encode(config.charset, 'replace')

    def negate(self):
        """ Negate the result of this term """
        self.negated = 1

    def pageFilter(self):
        """ Return a page filtering function

        This function is used to filter page list before we search
        it. Return a function that get a page name, and return bool.

        The default expression does not have any filter function and
        return None. Sub class may define custom filter functions.
        """
        return None

    def _get_matches(self, page):
        raise NotImplementedError

    def search(self, page):
        """ Search a page

        Returns a list of Match objects or None if term didn't find
        anything (vice versa if negate() was called).  Terms containing
        other terms must call this method to aggregate the results.
        This Base class returns True (Match()) if not negated.
        """
        logging.debug("%s searching page %r for (negated = %r) %r" % (self.__class__, page.page_name, self.negated, self._pattern))

        matches = self._get_matches(page)

        # Decide what to do with the results.
        if self.negated:
            if matches:
                result = None
            else:
                result = [Match()] # represents "matched" (but as it was a negative match, we have nothing to show)
        else: # not negated
            if matches:
                result = matches
            else:
                result = None
        logging.debug("%s returning %r" % (self.__class__, result))
        return result

    def highlight_re(self):
        """ Return a regular expression of what the term searches for

        Used to display the needle in the page.
        """
        return u''

    def _build_re(self, pattern, use_re=False, case=False, stemmed=False):
        """ Make a regular expression out of a text pattern """
        flags = case and re.U or (re.I | re.U)

        try:
            search_re = re.compile(pattern, flags)
        except re.error:
            pattern = re.escape(pattern)
            search_re = re.compile(pattern, flags)

        return pattern, search_re

    def _get_query_for_search_re(self, connection, field_to_check=None):
        """
        Return a query which satisfy self.search_re for field values.
        If field_to_check is given check values only for that field.
        """
        from MoinMoin.search.Xapian import Query

        queries = []

        documents = connection.get_all_documents()
        for document in documents:
            data = document.data
            if field_to_check:
                # Check only field with given name
                if field_to_check in data:
                    for term in data[field_to_check]:
                        if self.search_re.match(term):
                            queries.append(connection.query_field(field_to_check, term))
            else:
                # Check all fields
                for field, terms in data.iteritems():
                    for term in terms:
                        if self.search_re.match(term):
                            queries.append(connection.query_field(field_to_check, term))

        return Query(Query.OP_OR, queries)

    def xapian_need_postproc(self):
        return self.case

    def __unicode__(self):
        neg = self.negated and '-' or ''
        return u'%s%s"%s"' % (neg, self._tag, unicode(self._pattern))


class AndExpression(BaseExpression):
    """ A term connecting several sub terms with a logical AND """

    operator = ' '

    def __init__(self, *terms):
        self._subterms = list(terms)
        self.negated = 0

    def append(self, expression):
        """ Append another term """
        self._subterms.append(expression)

    def subterms(self):
        return self._subterms

    @property
    def costs(self):
        return sum([t.costs for t in self._subterms])

    def __unicode__(self):
        result = ''
        for t in self._subterms:
            result += self.operator + unicode(t)
        return u'[' + result[len(self.operator):] + u']'

    def _filter(self, terms, name):
        """ A function that returns True if all terms filter name """
        result = None
        for term in terms:
            _filter = term.pageFilter()
            t = _filter(name)
            if t is True:
                result = True
            elif t is False:
                result = False
                break
        logging.debug("pageFilter AND returns %r" % result)
        return result

    def pageFilter(self):
        """ Return a page filtering function

        This function is used to filter page list before we search it.

        Return a function that gets a page name, and return bool, or None.
        """
        # Sort terms by cost, then get all title searches
        self.sortByCost()
        terms = [term for term in self._subterms if isinstance(term, TitleSearch)]
        if terms:
            return lambda name: self._filter(terms, name)

    def sortByCost(self):
        self._subterms.sort(key=lambda t: t.costs)

    def search(self, page):
        """ Search for each term, cheap searches first """
        self.sortByCost()
        matches = []
        for term in self._subterms:
            result = term.search(page)
            if not result:
                return None
            matches.extend(result)
        return matches

    def highlight_re(self):
        result = []
        for s in self._subterms:
            highlight_re = s.highlight_re()
            if highlight_re:
                result.append(highlight_re)

        return u'|'.join(result)

    def xapian_need_postproc(self):
        for term in self._subterms:
            if term.xapian_need_postproc():
                return True
        return False

    def xapian_term(self, request, connection):
        from MoinMoin.search.Xapian import Query

        # sort negated terms
        terms = []
        not_terms = []

        for term in self._subterms:
            if not term.negated:
                terms.append(term.xapian_term(request, connection))
            else:
                not_terms.append(term.xapian_term(request, connection))

        # prepare query for not negated terms
        if terms:
            query = Query(Query.OP_AND, terms)
        else:
            query = Query('') # MatchAll

        # prepare query for negated terms
        if not_terms:
            query_negated = Query(Query.OP_OR, not_terms)
        else:
            query_negated = Query()

        return Query(Query.OP_AND_NOT, query, query_negated)


class OrExpression(AndExpression):
    """ A term connecting several sub terms with a logical OR """

    operator = ' or '

    def _filter(self, terms, name):
        """ A function that returns True if any term filters name """
        result = None
        for term in terms:
            _filter = term.pageFilter()
            t = _filter(name)
            if t is True:
                result = True
                break
            elif t is False:
                result = False
        logging.debug("pageFilter OR returns %r" % result)
        return result

    def search(self, page):
        """ Search page with terms

        @param page: the page instance
        """
        # XXX Do we have any reason to sort here? we are not breaking out
        # of the search in any case.
        #self.sortByCost()
        matches = []
        for term in self._subterms:
            result = term.search(page)
            if result:
                matches.extend(result)
        return matches

    def xapian_term(self, request, connection):
        from MoinMoin.search.Xapian import Query
        # XXX: negated terms managed by _moinSearch?
        return Query(Query.OP_OR, [term.xapian_term(request, connection) for term in self._subterms])


class BaseTextFieldSearch(BaseExpression):

    _field_to_search = None

    def xapian_term(self, request, connection):
        from MoinMoin.search.Xapian import Query, WikiAnalyzer

        if self.use_re:
            queries = [self._get_query_for_search_re(connection, self._field_to_search)]
        else:
            queries = []
            stemmed = []
            analyzer = WikiAnalyzer(language=app.cfg.language_default)

            for term in self._pattern.split():
                query_term = connection.query_field(self._field_to_search, term)
                tokens = analyzer.tokenize(term)

                if app.cfg.xapian_stemming:
                    query_token = []
                    for token, stemmed_ in tokens:
                        if token != term.lower():
                            if stemmed_:
                                query_token.append(Query(Query.OP_OR,
                                                         [connection.query_field(self._field_to_search, token),
                                                          connection.query_field(self._field_to_search, stemmed_)]))
#                                 stemmed.append('(%s|%s)' % (token, stemmed_))
                            else:
                                query_token.append(connection.query_field(self._field_to_search, token))
#                                 stemmed.append(token)
                    query_tokens = Query(Query.OP_AND, query_token)
                else:
                    query_tokens = Query(Query.OP_AND, [connection.query_field(self._field_to_search, token) for token, stemmed_ in tokens if token != term.lower()])

                queries.append(Query(Query.OP_OR, [query_term, query_tokens]))

            # XXX broken wrong regexp is built!
            if not self.case and stemmed:
                new_pat = ' '.join(stemmed)
                self._pattern = new_pat
                self.pattern, self.search_re = self._build_re(new_pat, use_re=False, case=self.case, stemmed=True)

        return Query(Query.OP_AND, queries)


class TextSearch(BaseTextFieldSearch):
    """ A term that does a normal text search

    Both page content and the page title are searched, using an
    additional TitleSearch term.
    """

    costs = 10000
    _field_to_search = 'content'

    def highlight_re(self):
        return u"(%s)" % self.pattern

    def _get_matches(self, page):
        matches = []

        # Search in page name
        results = TitleSearch(self._pattern, use_re=self.use_re, case=self.case)._get_matches(page)
        if results:
            matches.extend(results)

        # Search in page body
        body = page.get_raw_body()
        for match in self.search_re.finditer(body):
            matches.append(TextMatch(re_match=match))

        return matches

    def xapian_term(self, request, connection):
        from MoinMoin.search.Xapian import Query
        if self.use_re:
            # if regex search is wanted, we need to match all documents, because
            # we do not have full content stored and need post processing to do
            # the regex searching.
            return Query('') # MatchAll
        else:
            content_query = super(TextSearch, self).xapian_term(request, connection)
            title_query = TitleSearch(self._pattern, use_re=self.use_re, case=self.case).xapian_term(request, connection)
            return Query(OP_OR, [title_query, content_query])

    def xapian_need_postproc(self):
        # case-sensitive: xapian is case-insensitive, therefore we need postproc
        # regex: xapian can't do regex search. also we don't have full content
        #        stored (and we don't want to do that anyway), so regex search
        #        needs postproc also.
        return self.case or self.use_re


class TitleSearch(BaseTextFieldSearch):
    """ Term searches in pattern in page title only """

    _tag = 'title:'
    costs = 100
    _field_to_search = 'title'

    def pageFilter(self):
        """ Page filter function for single title search """

        def filter(name):
            match = self.search_re.search(name)
            result = bool(self.negated) ^ bool(match)
            logging.debug("pageFilter title returns %r (%r)" % (result, self.pattern))
            return result
        return filter

    def _get_matches(self, page):
        """ Get matches in page name """
        matches = []

        for match in self.search_re.finditer(page.page_name):
            matches.append(TitleMatch(re_match=match))

        return matches


class BaseFieldSearch(BaseExpression):

    _field_to_search = None

    def xapian_term(self, request, connection):
        if self.use_re:
            return self._get_query_for_search_re(connection, self._field_to_search)
        else:
            return connection.query_field(self._field_to_search, self._pattern)


class LinkSearch(BaseFieldSearch):
    """ Search the term in the pagelinks """

    _tag = 'linkto:'
    _field_to_search = 'linkto'
    costs = 5000 # cheaper than a TextSearch

    def __init__(self, pattern, use_re=False, case=True):
        """ Init a link search

        @param pattern: pattern to search for, ascii string or unicode
        @param use_re: treat pattern as re of plain text, bool
        @param case: do case sensitive search, bool
        """

        super(LinkSearch, self).__init__(pattern, use_re, case)

        self._textpattern = '(' + pattern.replace('/', '|') + ')' # used for search in text
        self.textsearch = TextSearch(self._textpattern, use_re=True, case=case)

    def highlight_re(self):
        return u"(%s)" % self._textpattern

    def _get_matches(self, page):
        # Get matches in page links
        matches = []

        # XXX in python 2.5 any() may be used.
        found = False
        for link in page.getPageLinks(page.request):
            if self.search_re.match(link):
                found = True
                break

        if found:
            # Search in page text
            results = self.textsearch.search(page)
            if results:
                matches.extend(results)
            else: # This happens e.g. for pages that use navigation macros
                matches.append(TextMatch(0, 0))

        return matches


class LanguageSearch(BaseFieldSearch):
    """ Search the pages written in a language """

    _tag = 'language:'
    _field_to_search = 'lang'
    costs = 5000 # cheaper than a TextSearch

    def __init__(self, pattern, use_re=False, case=False):
        """ Init a language search

        @param pattern: pattern to search for, ascii string or unicode
        @param use_re: treat pattern as re of plain text, bool
        @param case: do case sensitive search, bool
        """
        # iso language code, always lowercase and not case-sensitive
        super(LanguageSearch, self).__init__(pattern.lower(), use_re, case=False)

    def _get_matches(self, page):

        if self.pattern == page.pi['language']:
            return [Match()]
        else:
            return []


class MimetypeSearch(BaseFieldSearch):
    """ Search for files belonging to a specific mimetype """

    _tag = 'mimetype:'
    _field_to_search = 'mimetype'
    costs = 5000 # cheaper than a TextSearch

    def __init__(self, pattern, use_re=False, case=False):
        """ Init a mimetype search

        @param pattern: pattern to search for, ascii string or unicode
        @param use_re: treat pattern as re of plain text, bool
        @param case: do case sensitive search, bool
        """
        # always lowercase and not case-sensitive
        super(MimetypeSearch, self).__init__(pattern.lower(), use_re, case=False)

    def _get_matches(self, page):

        page_mimetype = u'text/%s' % page.pi['format']

        if self.search_re.search(page_mimetype):
            return [Match()]
        else:
            return []


class DomainSearch(BaseFieldSearch):
    """ Search for pages belonging to a specific domain """

    _tag = 'domain:'
    _field_to_search = 'domain'
    costs = 5000 # cheaper than a TextSearch

    def __init__(self, pattern, use_re=False, case=False):
        """ Init a domain search

        @param pattern: pattern to search for, ascii string or unicode
        @param use_re: treat pattern as re of plain text, bool
        @param case: do case sensitive search, bool
        """
        # always lowercase and not case-sensitive
        super(DomainSearch, self).__init__(pattern.lower(), use_re, case=False)

    def _get_matches(self, page):
        checks = {'standard': page.isStandardPage,
                  'system': lambda page=page: wikiutil.isSystemItem(page.page_name),
                 }

        try:
            match = checks[self.pattern]()
        except KeyError:
            match = False

        if match:
            return [Match()]
        else:
            return []

