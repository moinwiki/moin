# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
 MoinMoin - MoinMoin.search.analyzers Tests
"""


import py

from MoinMoin.security import ContentACL
from MoinMoin.search.analyzers import *


class TokenizerTestBase(object):

    def testTokenizer(self):
        """ analyzers: check what obtained tokens matched given """
        for value, expected_tokens in self.test_cases_query:
            tokens = [token.text for token in self.tokenizer(value)]
            assert set(expected_tokens) == set(tokens)


class TestAclTokenizer(TokenizerTestBase):
    """ analyzers: test ACL tokenizer """

    test_cases_query = [
        # (query, tokens)
        (u'-MinusGuy:read', [u'MinusGuy:-read']),
        (u'+PlusGuy:read', [u'PlusGuy:+read']),
        (u'Admin3:read,write,admin',
            [
             u'Admin3:+read',
             u'Admin3:+write',
             u'Admin3:-create',
             u'Admin3:+admin',
             u'Admin3:-destroy',
            ]
        ),
        (u'Admin1,Admin2:read,write,admin',
            [
             u'Admin1:+read',
             u'Admin1:+write',
             u'Admin1:-create',
             u'Admin1:+admin',
             u'Admin1:-destroy',
             u'Admin2:+read',
             u'Admin2:+write',
             u'Admin2:-create',
             u'Admin2:+admin',
             u'Admin2:-destroy',
            ]
        ),
        (u'JoeDoe:read,write',
            [
             u'JoeDoe:+read',
             u'JoeDoe:+write',
             u'JoeDoe:-create',
             u'JoeDoe:-admin',
             u'JoeDoe:-destroy',
            ]
        ),
        (u'name with spaces,another one:read,write',
            [
             u'name with spaces:+read',
             u'name with spaces:+write',
             u'name with spaces:-create',
             u'name with spaces:-admin',
             u'name with spaces:-destroy',
             u'another one:+read',
             u'another one:+write',
             u'another one:-create',
             u'another one:-admin',
             u'another one:-destroy',
            ]
        ),
        (u'CamelCase,extended name:read,write',
            [
             u'CamelCase:+read',
             u'CamelCase:+write',
             u'CamelCase:-create',
             u'CamelCase:-admin',
             u'CamelCase:-destroy',
             u'extended name:+read',
             u'extended name:+write',
             u'extended name:-create',
             u'extended name:-admin',
             u'extended name:-destroy',
            ]
        ),
        (u'BadGuy:',
            [
             u'BadGuy:-read',
             u'BadGuy:-write',
             u'BadGuy:-create',
             u'BadGuy:-admin',
             u'BadGuy:-destroy',
            ]
        ),
        (u'All:read',
            [
             u'All:+read',
             u'All:-write',
             u'All:-create',
             u'All:-admin',
             u'All:-destroy',
            ]
        )
    ]

    tokenizer = AclTokenizer()


class TestMimeTokenizer(TokenizerTestBase):
    """ analyzers: test content type analyzer """


    test_cases_query = [
                  # (query, tokens)
                  (u'text/plain', [u'text', u'plain']),
                  (u'text/plain;charset=utf-8', [u'text', u'plain', u'charset=utf-8']),
                  (u'text/html;value1=foo;value2=bar',
                   [u'text', u'html', u'value1=foo', u'value2=bar'],
                  ),
                  (u'text/html;value1=foo;value1=bar', [u'text', u'html', u'value1=bar'])
                 ]

    tokenizer = MimeTokenizer()


class TestItemNameAnalyzer(TokenizerTestBase):
    """ analyzers: test item_name analyzer """

    test_cases_query = [
                  # (query, tokens)
                  (u'wifi', [u'wifi']),
                  (u'WiFi', [u'wi', u'fi']),
                  (u'Wi-Fi', [u'wi', u'fi']),
                  (u'some item name', [u'some', u'item', u'name']),
                  (u'SomeItem/SubItem', [u'some', u'item', u'sub', u'item']),
                  (u'GSOC2011', [u'gsoc', u'2011'])
                 ]

    test_cases_index = [(u'some item name', [u'some', u'item', u'name']),
                        (u'SomeItem/SubItem', [u'some', u'item', u'sub', u'item', u'someitemsubitem']),
                        (u'GSOC2011', [u'gsoc', u'2011'])
                       ]

    tokenizer = item_name_analyzer()

    def testTokenizer(self):
        """ analyzers: test item name analyzer with "query" and "index" mode """

        for value, expected_tokens in self.test_cases_query:
            tokens = [token.text for token in self.tokenizer(value, mode="query")]
            assert set(expected_tokens) == set(tokens)
        for value, expected_tokens in self.test_cases_index:
            tokens = [token.text for token in self.tokenizer(value, mode="index")]
            assert set(expected_tokens) == set(tokens)
