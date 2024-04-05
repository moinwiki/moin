# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
 MoinMoin - moin.search.analyzers Tests
"""


from flask import current_app as app

from moin.search.analyzers import MimeTokenizer, AclTokenizer, item_name_analyzer


class TokenizerTestBase:

    def testTokenizer(self):
        """analyzers: check what obtained tokens matched given"""
        tokenizer = self.make_tokenizer()
        for value, expected_tokens in self.test_cases_query:
            tokens = [token.text for token in tokenizer(value)]
            assert set(expected_tokens) == set(tokens)


class TestAclTokenizer(TokenizerTestBase):
    """analyzers: test ACL tokenizer"""

    test_cases_query = [
        # (query, tokens)
        ("-MinusGuy:read", ["MinusGuy:-read"]),
        ("+PlusGuy:read", ["PlusGuy:+read"]),
        (
            "Admin3:read,write,admin",
            ["Admin3:+read", "Admin3:-pubread", "Admin3:+write", "Admin3:-create", "Admin3:+admin", "Admin3:-destroy"],
        ),
        (
            "Admin1,Admin2:read,write,admin",
            [
                "Admin1:+read",
                "Admin1:-pubread",
                "Admin1:+write",
                "Admin1:-create",
                "Admin1:+admin",
                "Admin1:-destroy",
                "Admin2:+read",
                "Admin2:-pubread",
                "Admin2:+write",
                "Admin2:-create",
                "Admin2:+admin",
                "Admin2:-destroy",
            ],
        ),
        (
            "JoeDoe:pubread,write",
            ["JoeDoe:-read", "JoeDoe:+pubread", "JoeDoe:+write", "JoeDoe:-create", "JoeDoe:-admin", "JoeDoe:-destroy"],
        ),
        (
            "name with spaces,another one:read,write",
            [
                "name with spaces:+read",
                "name with spaces:-pubread",
                "name with spaces:+write",
                "name with spaces:-create",
                "name with spaces:-admin",
                "name with spaces:-destroy",
                "another one:+read",
                "another one:-pubread",
                "another one:+write",
                "another one:-create",
                "another one:-admin",
                "another one:-destroy",
            ],
        ),
        (
            "CamelCase,extended name:read,write",
            [
                "CamelCase:+read",
                "CamelCase:-pubread",
                "CamelCase:+write",
                "CamelCase:-create",
                "CamelCase:-admin",
                "CamelCase:-destroy",
                "extended name:+read",
                "extended name:-pubread",
                "extended name:+write",
                "extended name:-create",
                "extended name:-admin",
                "extended name:-destroy",
            ],
        ),
        (
            "BadGuy:",
            ["BadGuy:-read", "BadGuy:-pubread", "BadGuy:-write", "BadGuy:-create", "BadGuy:-admin", "BadGuy:-destroy"],
        ),
        ("All:read", ["All:+read", "All:-pubread", "All:-write", "All:-create", "All:-admin", "All:-destroy"]),
    ]

    def make_tokenizer(self):
        return AclTokenizer(app.cfg.acl_rights_contents)


class TestMimeTokenizer(TokenizerTestBase):
    """analyzers: test content type analyzer"""

    test_cases_query = [
        # (query, tokens)
        (
            "text/x.moin.wiki;charset=utf-8",
            [
                "text/x.moin.wiki;charset=utf-8",
                "text",
                "moinwiki",
                "x.moin.wiki",
                "x",
                "moin",
                "wiki",
                "charset=utf-8",
                "charset",
                "utf-8",
            ],
        ),
        ("text/plain", ["text/plain", "text", "plain"]),
        (
            "text/plain;charset=utf-8",
            ["text/plain;charset=utf-8", "text", "plain", "charset=utf-8", "charset", "utf-8"],
        ),
        (
            "text/html;value1=foo;value2=bar",
            [
                "text/html;value1=foo;value2=bar",
                "text",
                "html",
                "value1=foo",
                "value1",
                "foo",
                "value2=bar",
                "value2",
                "bar",
            ],
        ),
        # we normalize, sort the params:
        (
            "text/html;value2=bar;value1=foo",
            [
                "text/html;value2=bar;value1=foo",
                "text",
                "html",
                "value2=bar",
                "value2",
                "bar",
                "value1=foo",
                "value1",
                "foo",
            ],
        ),
    ]

    def make_tokenizer(self):
        return MimeTokenizer()


class TestItemNameAnalyzer(TokenizerTestBase):
    """analyzers: test item_name analyzer"""

    test_cases_query = [
        # (query, tokens)
        ("wifi", ["wifi"]),
        ("WiFi", ["wi", "fi"]),
        ("Wi-Fi", ["wi", "fi"]),
        ("some item name", ["some", "item", "name"]),
        ("SomeItem/SubItem", ["some", "item", "sub", "item"]),
        ("GSOC2011", ["gsoc", "2011"]),
    ]

    test_cases_index = [
        ("some item name", ["some", "item", "name"]),
        ("SomeItem/SubItem", ["some", "item", "sub", "item", "someitemsubitem"]),
        ("GSOC2011", ["gsoc", "2011"]),
    ]

    def make_tokenizer(self):
        return item_name_analyzer()

    def testTokenizer(self):
        """analyzers: test item name analyzer with "query" and "index" mode"""
        tokenizer = self.make_tokenizer()
        for value, expected_tokens in self.test_cases_query:
            tokens = [token.text for token in tokenizer(value, mode="query")]
            assert set(expected_tokens) == set(tokens)
        for value, expected_tokens in self.test_cases_index:
            tokens = [token.text for token in tokenizer(value, mode="index")]
            assert set(expected_tokens) == set(tokens)
