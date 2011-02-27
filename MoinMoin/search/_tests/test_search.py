"""
    MoinMoin - MoinMoin.search Tests

    We exclude underlay/system pages for some search tests to save time.

    @copyright: 2005 by Nir Soffer <nirs@freeshell.org>,
                2007-2010 by MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""


import os, StringIO, time

import py

py.test.skip("broken")

from MoinMoin.search import QueryError, _get_searcher
from MoinMoin.search.queryparser import QueryParser
from MoinMoin.search.builtin import MoinSearch
from MoinMoin._tests import nuke_xapian_index, wikiconfig, become_trusted, create_item
from MoinMoin.wikiutil import Version

PY_MIN_VERSION = '1.0.0'
if Version(version=py.version) < Version(version=PY_MIN_VERSION):
    # There are some generative tests, which won't run on older versions!
    # XXX These tests should be refactored to be able to be run with older versions of py.
    py.test.skip('Currently py version %s is needed' % PY_MIN_VERSION)


class TestQueryParsing(object):
    """ search: query parser tests """

    def testQueryParser(self):
        """ search: test the query parser """
        parser = QueryParser()
        for query, wanted in [
            # Even a single term is a and expression (this is needed for xapian because it
            # only has AND_NOT, but not a simple NOT).  This is why we have many many brackets here.
            ("a", '["a"]'),
            ("-a", '[-"a"]'),
            ("a b", '["a" "b"]'),
            ("a -b c", '["a" -"b" "c"]'),
            ("aaa bbb -ccc", '["aaa" "bbb" -"ccc"]'),
            ("title:aaa title:bbb -title:ccc", '[title:"aaa" title:"bbb" -title:"ccc"]'),
            ("title:case:aaa title:re:bbb -title:re:case:ccc", '[title:case:"aaa" title:re:"bbb" -title:re:case:"ccc"]'),
            ("linkto:aaa", '[linkto:"aaa"]'),
            ("domain:aaa", '[domain:"aaa"]'),
            ("re:case:title:aaa", '[title:re:case:"aaa"]'),
            ("(aaa or bbb) and (ccc or ddd)", '[[[["aaa"] or ["bbb"]]] [[["ccc"] or ["ddd"]]]]'),
            ("(aaa or bbb) (ccc or ddd)", '[[[["aaa"] or ["bbb"]]] [[["ccc"] or ["ddd"]]]]'),
            ("aaa or bbb", '[[["aaa"] or ["bbb"]]]'),
            ("aaa or bbb or ccc", '[[["aaa"] or [[["bbb"] or ["ccc"]]]]]'),
            ("aaa or bbb and ccc", '[[["aaa"] or ["bbb" "ccc"]]]'),
            ("aaa and bbb or ccc", '[[["aaa" "bbb"] or ["ccc"]]]'),
            ("aaa and bbb and ccc", '["aaa" "bbb" "ccc"]'),
            ("aaa or bbb and ccc or ddd", '[[["aaa"] or [[["bbb" "ccc"] or ["ddd"]]]]]'),
            ("aaa or bbb ccc or ddd", '[[["aaa"] or [[["bbb" "ccc"] or ["ddd"]]]]]'),
            ("(HelpOn) (Administration)", '[["HelpOn"] ["Administration"]]'),
            ("(HelpOn) (-Administration)", '[["HelpOn"] [-"Administration"]]'),
            ("(HelpOn) and (-Administration)", '[["HelpOn"] [-"Administration"]]'),
            ("(HelpOn) and (Administration) or (Configuration)", '[[[["HelpOn"] ["Administration"]] or [["Configuration"]]]]'),
            ("(a) and (b) or (c) or -d", '[[[["a"] ["b"]] or [[[["c"]] or [-"d"]]]]]'),
            ("a b c d e or f g h", '[[["a" "b" "c" "d" "e"] or ["f" "g" "h"]]]'),
            ('"no', '[""no"]'),
            ('no"', '["no""]'),
            ("'no", "[\"'no\"]"),
            ("no'", "[\"no'\"]"),
            ('"no\'', '[""no\'"]')]:
            result = parser.parse_query(query)
            assert str(result) == wanted

    def testQueryParserExceptions(self):
        """ search: test the query parser """
        parser = QueryParser()

        def _test(q):
            py.test.raises(QueryError, parser.parse_query, q)

        for query in ['""', '(', ')', '(a or b']:
            yield _test, query


class BaseSearchTest(object):
    """ search: test search """
    doesnotexist = u'jfhsdaASDLASKDJ'

    class Config(wikiconfig.Config):
        load_xml = wikiconfig.Config._test_items_xml

    # key - page name, value - page content. If value is None page
    # will not be created but will be used for a search. None should
    # be used for pages which already exist.
    pages = {u'SearchTestPage': u'this is a test page',
             u'SearchTestLinks': u'SearchTestPage',
             u'SearchTestLinksLowerCase': u'searchtestpage',
             u'SearchTestOtherLinks': u'SearchTestLinks',
             u'TestEdit': u'TestEdit',
             u'TestOnEditing': u'another test page',
             u'ContentSearchUpper': u'Find the NEEDLE in the haystack.',
             u'ContentSearchLower': u'Find the needle in the haystack.',
             u'LanguageSetup': None,
             u'HomePageWiki': None,
             u'FrontPage': None,
             u'RecentChanges': None,
             u'HelpOnCreoleSyntax': None,
             u'HelpIndex': None,
            }

    searcher_class = None

    def _index_update(self):
        pass

    @classmethod
    def setup_class(cls):
        pass

    def teardown_class(self):
        pass

    def setup_method(cls, method):
        request = cls.request
        become_trusted()

        for page, text in cls.pages.iteritems():
            if text:
                create_item(page, text)

    def get_searcher(self, query):
        raise NotImplementedError

    def search(self, query):
        if isinstance(query, str) or isinstance(query, unicode):
            query = QueryParser().parse_query(query)

        return self.get_searcher(query).run()

    def test_title_search_simple(self):
        searches = {u'title:SearchTestPage': 1,
                    u'title:LanguageSetup': 1,
                    u'title:HelpIndex': 1,
                    u'title:Help': 2,
                    u'title:TestOn': 1,
                    u'title:SearchTestNotExisting': 0,
                    u'title:FrontPage': 1,
                    u'title:TestOnEditing': 1,
                   }

        def test(query, res_count):
            result = self.search(query)
            test_result = len(result.hits)
            assert test_result == res_count

        for query, res_count in searches.iteritems():
            yield query, test, query, res_count

    def test_title_search_re(self):
        expected_pages = set([u'SearchTestPage', u'SearchTestLinks', u'SearchTestLinksLowerCase', u'SearchTestOtherLinks', ])
        result = self.search(ur'-domain:underlay -domain:system title:re:\bSearchTest')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(ur'-domain:underlay -domain:system title:re:\bSearchTest\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_title_search_case(self):
        expected_pages = set([u'SearchTestPage', ])
        result = self.search(u'-domain:underlay -domain:system title:case:SearchTestPage')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(u'-domain:underlay -domain:system title:case:searchtestpage')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_title_search_case_re(self):
        expected_pages = set([u'SearchTestPage', ])
        result = self.search(ur'-domain:underlay -domain:system title:case:re:\bSearchTestPage\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(ur'-domain:underlay -domain:system title:case:re:\bsearchtestpage\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_linkto_search_simple(self):
        expected_pages = set([u'SearchTestLinks', ])
        result = self.search(u'-domain:underlay -domain:system linkto:SearchTestPage')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(u'-domain:underlay -domain:system linkto:SearchTestNotExisting')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_linkto_search_re(self):
        expected_pages = set([u'SearchTestLinks', u'SearchTestOtherLinks', ])
        result = self.search(ur'-domain:underlay -domain:system linkto:re:\bSearchTest')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(ur'-domain:underlay -domain:system linkto:re:\bSearchTest\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_linkto_search_case(self):
        expected_pages = set([u'SearchTestLinks', ])
        result = self.search(u'-domain:underlay -domain:system linkto:case:SearchTestPage')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(u'-domain:underlay -domain:system linkto:case:searchtestpage')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_linkto_search_case_re(self):
        expected_pages = set([u'SearchTestLinks', ])
        result = self.search(ur'-domain:underlay -domain:system linkto:case:re:\bSearchTestPage\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(ur'-domain:underlay -domain:system linkto:case:re:\bsearchtestpage\b')
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def test_mimetype_search_simple(self):
        result = self.search(u'mimetype:text/wiki')
        test_result = len(result.hits)
        assert test_result == 14

    def test_mimetype_search_re(self):
        result = self.search(ur'mimetype:re:\btext/wiki\b')
        test_result = len(result.hits)
        assert test_result == 14

    def test_language_search_simple(self):
        result = self.search(u'language:en')
        test_result = len(result.hits)
        assert test_result == 14

    def test_domain_search_simple(self):
        result = self.search(u'domain:system')
        assert result.hits

    def test_search_and(self):
        """ search: title search with AND expression """
        expected_pages = set([u'HelpOnCreoleSyntax', ])
        result = self.search(u"title:HelpOnCreoleSyntax lang:en")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        result = self.search(u"title:HelpOnCreoleSyntax lang:de")
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

        result = self.search(u"title:Help title:%s" % self.doesnotexist)
        found_pages = set([hit.page_name for hit in result.hits])
        assert not found_pages

    def testTitleSearchOR(self):
        """ search: title search with OR expression """
        expected_pages = set([u'FrontPage', u'RecentChanges', ])
        result = self.search(u"title:FrontPage or title:RecentChanges")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

    def testTitleSearchNegatedFindAll(self):
        """ search: negated title search for some pagename that does not exist results in all pagenames """
        result = self.search(u"-title:%s" % self.doesnotexist)
        n_pages = len(self.pages)
        test_result = len(result.hits)
        assert test_result == n_pages

    def testTitleSearchNegativeTerm(self):
        """ search: title search for a AND expression with a negative term """
        result = self.search(u"-title:FrontPage")
        found_pages = set([hit.page_name for hit in result.hits])
        assert u'FrontPage' not in found_pages
        test_result = len(result.hits)
        n_pages = len(self.pages) - 1
        assert test_result == n_pages

        result = self.search(u"-title:HelpOn")
        test_result = len(result.hits)
        n_pages = len(self.pages) - 1
        assert test_result == n_pages

    def testFullSearchNegatedFindAll(self):
        """ search: negated full search for some string that does not exist results in all pages """
        result = self.search(u"-%s" % self.doesnotexist)
        test_result = len(result.hits)
        n_pages = len(self.pages)
        assert test_result == n_pages

    def testFullSearchRegexCaseInsensitive(self):
        """ search: full search for regular expression (case insensitive) """
        search_re = 'ne{2}dle' # matches 'NEEDLE' or 'needle' or ...
        expected_pages = set(['ContentSearchUpper', 'ContentSearchLower', ])
        result = self.search(u'-domain:underlay -domain:system re:%s' % search_re)
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

    def testFullSearchRegexCaseSensitive(self):
        """ search: full search for regular expression (case sensitive) """
        search_re = 'ne{2}dle' # matches 'needle'
        expected_pages = set(['ContentSearchLower', ])
        result = self.search(u'-domain:underlay -domain:system re:case:%s' % search_re)
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

    def testFullSearchNegativeTerm(self):
        """ search: full search for a AND expression with a negative term """
        helpon_count = len(self.search(u"HelpOn").hits)
        result = self.search(u"HelpOn -Thumbnails")
        assert 0 < len(result.hits) < helpon_count

    def test_title_search(self):
        expected_pages = set(['FrontPage', ])
        query = QueryParser(titlesearch=True).parse_query('FrontPage')
        result = self.search(query)
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

    def test_get_searcher(self):
        assert isinstance(_get_searcher(self.request, ''), self.searcher_class)


class TestMoinSearch(BaseSearchTest):
    """ search: test Moin search """
    searcher_class = MoinSearch

    def get_searcher(self, query):
        pages = [{'pagename': page, 'attachment': '', 'wikiname': 'Self', } for page in self.pages]
        return MoinSearch(self.request, query, pages=pages)

    def test_stemming(self):
        expected_pages = set([u'TestEdit', u'TestOnEditing', ])
        result = self.search(u"title:edit")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        expected_pages = set([u'TestOnEditing', ])
        result = self.search(u"title:editing")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages


class TestXapianSearch(BaseSearchTest):
    """ search: test Xapian indexing / search """

    class Config(wikiconfig.Config):
        xapian_search = True

    def _index_update(self):
        # for xapian, we queue index updates so they can get indexed later.
        # here we make sure the queue will be processed completely,
        # before we continue:
        from MoinMoin.search.Xapian import XapianIndex
        XapianIndex(self.request).do_queued_updates()

    def get_searcher(self, query):
        from MoinMoin.search.Xapian.search import XapianSearch
        return XapianSearch(self.request, query)

    def get_moin_search_connection(self):
        from MoinMoin.search.Xapian import XapianIndex
        return XapianIndex(self.request).get_search_connection()

    def setup_class(self):
        py.test.skip("xapian tests broken")
        try:
            from MoinMoin.search.Xapian import XapianIndex
            from MoinMoin.search.Xapian.search import XapianSearch
            self.searcher_class = XapianSearch

        except ImportError, error:
            if not str(error).startswith('Xapian '):
                raise
            py.test.skip('xapian is not installed')

        nuke_xapian_index()
        index = XapianIndex(self.request)
        # Additionally, pages which were not created but supposed to be searched
        # are indexed.
        pages_to_index = [page for page in self.pages if not self.pages[page]]
        index.indexPages(mode='add', pages=pages_to_index)

        super(TestXapianSearch, self).setup_class()

    def teardown_class(self):
        nuke_xapian_index()

    def test_get_all_documents(self):
        connection = self.get_moin_search_connection()
        documents = connection.get_all_documents()
        n_pages = len(self.pages)
        test_result = len(documents)
        assert test_result == n_pages
        for document in documents:
            assert document.data['pagename'][0] in self.pages.keys()

    def test_xapian_term(self):
        parser = QueryParser()
        connection = self.get_moin_search_connection()

        prefixes = {u'': ([u'', u're:', u'case:', u'case:re:'], u'SearchTestPage'),
                    u'title:': ([u'', u're:', u'case:', u'case:re:'], u'SearchTestPage'),
                    u'linkto:': ([u'', u're:', u'case:', u'case:re:'], u'FrontPage'),
                    u'mimetype:': ([u'', u're:'], u'text/wiki'),
                    u'language:': ([u''], u'en'),
                    u'domain:': ([u''], u'system'),
                   }

        def test_query(query):
            query_ = parser.parse_query(query).xapian_term(self.request, connection)
            print str(query_)
            assert not query_.empty()

        for prefix, data in prefixes.iteritems():
            modifiers, term = data
            for modifier in modifiers:
                query = ''.join([prefix, modifier, term])
                yield query, test_query, query

    def test_stemming(self):
        expected_pages = set([u'TestEdit', ])
        result = self.search(u"title:edit")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        expected_pages = set([u'TestOnEditing', ])
        result = self.search(u"title:editing")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages


class TestXapianSearchStemmed(TestXapianSearch):
    """ search: test Xapian indexing / search - with stemming enabled """

    class Config(wikiconfig.Config):
        xapian_search = True
        xapian_stemming = True

    def test_stemming(self):
        expected_pages = set([u'TestEdit', u'TestOnEditing', ])
        result = self.search(u"title:edit")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages

        expected_pages = set([u'TestEdit', u'TestOnEditing', ])
        result = self.search(u"title:editing")
        found_pages = set([hit.page_name for hit in result.hits])
        assert found_pages == expected_pages


class TestGetSearcher(object):

    class Config(wikiconfig.Config):
        xapian_search = True

    def test_get_searcher(self):
        assert isinstance(_get_searcher(self.request, ''), MoinSearch), 'Xapian index is not created, despite the configuration, MoinSearch must be used!'

coverage_modules = ['MoinMoin.search']

