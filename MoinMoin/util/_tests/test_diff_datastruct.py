# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.diff_datastruct Tests
"""

import pytest

from MoinMoin.util.diff_datastruct import diff, make_text_diff, Undefined, INSERT, DELETE


class TestDiffDatastruct(object):

    def _test_make_text_diff(self, tests):
        for changes, expected in tests:
            for got in make_text_diff(changes):
                assert got == expected

    def test_diff_no_change(self):
        datastruct = [None, True, 42, u"value", [1, 2, 3], dict(one=1, two=2)]
        for d in datastruct:
            assert diff(d, d) == []

    def test_diff_none(self):
        tests = [(None, None, []),
                 (Undefined, None, [(INSERT, [], None)]),
                 (None, Undefined, [(DELETE, [], None)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_bool(self):
        tests = [(True, True, []),
                 (Undefined, True, [(INSERT, [], True)]),
                 (True, Undefined, [(DELETE, [], True)]),
                 (True, False, [(DELETE, [], True), (INSERT, [], False)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_int(self):
        tests = [(1, 1, []),
                 (Undefined, 2, [(INSERT, [], 2)]),
                 (2, Undefined, [(DELETE, [], 2)]),
                 (3, 4, [(DELETE, [], 3), (INSERT, [], 4)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_float(self):
        tests = [(1.1, 1.1, []),
                 (Undefined, 2.2, [(INSERT, [], 2.2)]),
                 (2.2, Undefined, [(DELETE, [], 2.2)]),
                 (3.3, 4.4, [(DELETE, [], 3.3), (INSERT, [], 4.4)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_unicode(self):
        tests = [(u"same", u"same", []),
                 (Undefined, u"new", [(INSERT, [], u"new")]),
                 (u"old", Undefined, [(DELETE, [], u"old")]),
                 (u"some value", u"some other value",
                  [(DELETE, [], u"some value"), (INSERT, [], u"some other value")])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_list(self):
        tests = [([1], [1], []),
                 (Undefined, [2], [(INSERT, [], [2])]),
                 ([2], Undefined, [(DELETE, [], [2])]),
                 ([1, 2], [2, 3], [(DELETE, [], [1]), (INSERT, [], [3])]),
                 ([9, 8], [8, 7, 6, 5], [(DELETE, [], [9]), (INSERT, [], [7, 6, 5])])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_dict(self):
        tests = [(dict(same=1), dict(same=1), []),
                 (Undefined, dict(new=1), [(INSERT, ["new"], 1)]),
                 (dict(old=1), Undefined, [(DELETE, ["old"], 1)]),
                 (dict(same=1, old=2), dict(same=1, new1=3, new2=4),
                  [(INSERT, ["new1"], 3), (INSERT, ["new2"], 4),
                   (DELETE, ["old"], 2)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_nested_dict(self):
        tests = [(dict(key=dict(same=None)), dict(key=dict(same=None)), []),
                 (dict(key=dict()), dict(key=dict(added=None)), [(INSERT, ["key", "added"], None)]),
                 (dict(key=dict(removed=None)), dict(key=dict()), [(DELETE, ["key", "removed"], None)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_str_unicode_keys(self):
        d1 = {"old": u"old", u"same1": u"same1", "same2": u"same2"}
        d2 = {u"new": u"new", "same1": u"same1", u"same2": u"same2"}
        assert diff(d1, d2) == [(INSERT, ["new"], u"new"),
                                (DELETE, ["old"], u"old")]

    def test_diff_errors(self):
        tests = [(u"foo", True),
                 ((1, 2, ), (3, 4, )),
                 (dict(key=(1, 2, )), dict()),
                 (None, [1, 2, ])]
        for d1, d2 in tests:
            with pytest.raises(TypeError):
                diff(d1, d2)

    def test_make_text_diff_empty(self):
        for got in make_text_diff([]):
            assert got == u""

    def test_make_text_diff_none(self):
        tests = [([(INSERT, [], None)], u"+ None"),
                 ([(DELETE, [], None)], u"- None")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_bool(self):
        tests = [([(INSERT, [], True)], u"+ True"),
                 ([(DELETE, [], False)], u"- False")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_int(self):
        tests = [([(INSERT, [], 123)], u"+ 123"),
                 ([(DELETE, [], 321)], u"- 321")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_float(self):
        tests = [([(INSERT, [], 1.2)], u"+ 1.2"),
                 ([(DELETE, [], 3.4)], u"- 3.4")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_unicode(self):
        tests = [([(INSERT, [], u"new value")], u"+ new value"),
                 ([(DELETE, [], u"old value")], u"- old value")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_list(self):
        tests = [([(INSERT, [], [1, 2, 3, ])], u"+ [1, 2, 3]"),
                 ([(DELETE, [], [4, 5, ])], u"- [4, 5]")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_one_key(self):
        tests = [([(INSERT, ["key"], u"new value")], u"+ key: new value"),
                 ([(DELETE, ["key"], u"old value")], u"- key: old value")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_multiple_keys(self):
        tests = [([(INSERT, ["key1", "key2"], 1)], u"+ key1.key2: 1"),
                 ([(DELETE, ["key1", "key2", "key3"], 2)], u"- key1.key2.key3: 2")]
        self._test_make_text_diff(tests)
