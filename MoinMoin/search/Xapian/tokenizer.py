"""
    MoinMoin - A text analyzer for wiki syntax

    @copyright: 2006-2008 MoinMoin:ThomasWaldmann,
                2006 MoinMoin:FranzPletz
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import re
import xapian

from flask import current_app as app

from MoinMoin.parser.text_moin_wiki import Parser as WikiParser
from MoinMoin import config


class WikiAnalyzer(object):
    """ A text analyzer for wiki syntax

    The purpose of this class is to analyze texts/pages in wiki syntax
    and yield single terms to feed into the xapian database.
    """

    singleword = r"[%(u)s][%(l)s]+" % {
                     'u': config.chars_upper,
                     'l': config.chars_lower,
                 }

    singleword_re = re.compile(singleword, re.U)
    wikiword_re = re.compile(WikiParser.word_rule, re.UNICODE|re.VERBOSE)

    token_re = re.compile(
        r"(?P<company>\w+[&@]\w+)|" + # company names like AT&T and Excite@Home.
        r"(?P<email>\w+([.-]\w+)*@\w+([.-]\w+)*)|" +    # email addresses
        r"(?P<acronym>(\w\.)+)|" +          # acronyms: U.S.A., I.B.M., etc.
        r"(?P<word>\w+)",                   # words (including WikiWords)
        re.U)

    dot_re = re.compile(r"[-_/,.]")
    mail_re = re.compile(r"[-_/,.]|(@)")
    alpha_num_re = re.compile(r"\d+|\D+")

    def __init__(self, language=None):
        """
        @param language: if given, the language in which to stem words
        """
        self.stemmer = None
        if app.cfg.xapian_stemming and language:
            try:
                stemmer = xapian.Stem(language)
                # we need this wrapper because the stemmer returns a utf-8
                # encoded string even when it gets fed with unicode objects:
                self.stemmer = lambda word: stemmer(word).decode('utf-8')
            except xapian.InvalidArgumentError:
                # lang is not stemmable or not available
                pass

    def raw_tokenize_word(self, word, pos):
        """ try to further tokenize some word starting at pos """
        yield (word, pos)
        if self.wikiword_re.match(word):
            # if it is a CamelCaseWord, we additionally try to tokenize Camel, Case and Word
            for m in re.finditer(self.singleword_re, word):
                mw, mp = m.group(), pos + m.start()
                for w, p in self.raw_tokenize_word(mw, mp):
                    yield (w, p)
        else:
            # if we have Foo42, yield Foo and 42
            for m in re.finditer(self.alpha_num_re, word):
                mw, mp = m.group(), pos + m.start()
                if mw != word:
                    for w, p in self.raw_tokenize_word(mw, mp):
                        yield (w, p)

    def raw_tokenize(self, value):
        """ Yield a stream of words from a string.

        @param value: string to split, must be an unicode object or a list of
                      unicode objects
        """
        if isinstance(value, list): # used for page links
            for v in value:
                yield (v, 0)
        else:
            tokenstream = re.finditer(self.token_re, value)
            for m in tokenstream:
                if m.group("acronym"):
                    yield (m.group("acronym").replace('.', ''), m.start())
                elif m.group("company"):
                    yield (m.group("company"), m.start())
                elif m.group("email"):
                    displ = 0
                    for word in self.mail_re.split(m.group("email")):
                        if word:
                            yield (word, m.start() + displ)
                            displ += len(word) + 1
                elif m.group("word"):
                    for word, pos in self.raw_tokenize_word(m.group("word"), m.start()):
                        yield word, pos

    def tokenize(self, value):
        """
        Yield a stream of raw lower cased and stemmed words from a string.

        @param value: string to split, must be an unicode object or a list of
                      unicode objects
        """
        if self.stemmer:

            def stemmer(value):
                stemmed = self.stemmer(value)
                if stemmed != value:
                    return stemmed
                else:
                    return ''
        else:
            stemmer = lambda v: ''

        for word, pos in self.raw_tokenize(value):
            # Xapian stemmer expects lowercase input
            word = word.lower()
            yield word, stemmer(word)

