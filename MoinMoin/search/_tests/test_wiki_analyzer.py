# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.search.Xapian.tokenizer Tests

    @copyright: 2009 MoinMoin:DmitrijsMilajevs
    @license: GNU GPL, see COPYING for details.
"""

import py

from flask import current_app as app

from MoinMoin._tests import wikiconfig

try:
    from MoinMoin.search.Xapian.tokenizer import WikiAnalyzer
except ImportError:
    py.test.skip('xapian is not installed')

class TestWikiAnalyzer(object):

    word = u'HelpOnMoinTesting'
    words = {word.lower(): u'',
             u'help': u'',
             u'on': u'',
             u'moin': u'',
             u'testing': u''}

    def setup_class(self):
        self.analyzer = WikiAnalyzer(language=app.cfg.language_default)

    def test_tokenize(self):
        words = self.words
        tokens = list(self.analyzer.tokenize(self.word))

        assert len(tokens) == len(words)

        for token, stemmed in tokens:
            assert token in words
            assert words[token] == stemmed


class TestWikiAnalyzerStemmed(TestWikiAnalyzer):

    word = u'HelpOnMoinTesting'
    words = {word.lower(): u'helponmointest',
             u'help': u'',
             u'on': u'',
             u'moin': u'',
             u'testing': u'test'}

    class Config(wikiconfig.Config):

        xapian_stemming = True


class TestWikiAnalyzerSeveralWords(TestWikiAnalyzer):

    word = u'HelpOnMoinTesting OtherWikiWord'
    words = {u'helponmointesting': u'',
             u'help': u'',
             u'on': u'',
             u'moin': u'',
             u'testing': u'',
             u'otherwikiword': u'',
             u'other': u'',
             u'wiki': u'',
             u'word': u''}


class TestWikiAnalyzerStemmedSeveralWords(TestWikiAnalyzer):

    word = u'HelpOnMoinTesting OtherWikiWord'
    words = {u'helponmointesting': u'helponmointest',
             u'help': u'',
             u'on': u'',
             u'moin': u'',
             u'testing': u'test',
             u'otherwikiword': u'',
             u'other': u'',
             u'wiki': u'',
             u'word': u''}

    class Config(wikiconfig.Config):

        xapian_stemming = True


class TestWikiAnalyzerStemmedHelpOnEditing(TestWikiAnalyzer):

    word = u'HelpOnEditing'
    words = {u'helponediting': u'helponedit',
             u'help': u'',
             u'on': u'',
             u'editing': u'edit'}

    class Config(wikiconfig.Config):

        xapian_stemming = True


class TestWikiAnalyzerStemmedCategoryHomepage(TestWikiAnalyzer):

    word = u'CategoryHomepage'
    words = {u'categoryhomepage': u'categoryhomepag',
             u'category': u'categori',
             u'homepage': u'homepag'}

    class Config(wikiconfig.Config):

        xapian_stemming = True
