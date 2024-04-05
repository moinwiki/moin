# Copyright: 2013 MoinMoin:AnaBalica
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.diff_datastruct Tests
"""

import pytest

from moin.utils.diff_datastruct import diff, make_text_diff, Undefined, INSERT, DELETE


class TestDiffDatastruct:

    def _test_make_text_diff(self, tests):
        for changes, expected in tests:
            for got in make_text_diff(changes):
                assert got == expected

    def test_diff_no_change(self):
        datastruct = [None, True, 42, "value", [1, 2, 3], dict(one=1, two=2)]
        for d in datastruct:
            assert diff(d, d) == []

    def test_diff_none(self):
        tests = [(None, None, []), (Undefined, None, [(INSERT, [], None)]), (None, Undefined, [(DELETE, [], None)])]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_bool(self):
        tests = [
            (True, True, []),
            (Undefined, True, [(INSERT, [], True)]),
            (True, Undefined, [(DELETE, [], True)]),
            (True, False, [(DELETE, [], True), (INSERT, [], False)]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_int(self):
        tests = [
            (1, 1, []),
            (Undefined, 2, [(INSERT, [], 2)]),
            (2, Undefined, [(DELETE, [], 2)]),
            (3, 4, [(DELETE, [], 3), (INSERT, [], 4)]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_float(self):
        tests = [
            (1.1, 1.1, []),
            (Undefined, 2.2, [(INSERT, [], 2.2)]),
            (2.2, Undefined, [(DELETE, [], 2.2)]),
            (3.3, 4.4, [(DELETE, [], 3.3), (INSERT, [], 4.4)]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_unicode(self):
        tests = [
            ("same", "same", []),
            (Undefined, "new", [(INSERT, [], "new")]),
            ("old", Undefined, [(DELETE, [], "old")]),
            ("some value", "some other value", [(DELETE, [], "some value"), (INSERT, [], "some other value")]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_list(self):
        tests = [
            ([1], [1], []),
            (Undefined, [2], [(INSERT, [], [2])]),
            ([2], Undefined, [(DELETE, [], [2])]),
            ([1, 2], [2, 3], [(DELETE, [], [1]), (INSERT, [], [3])]),
            ([9, 8], [8, 7, 6, 5], [(DELETE, [], [9]), (INSERT, [], [7, 6, 5])]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_dict(self):
        tests = [
            (dict(same=1), dict(same=1), []),
            (Undefined, dict(new=1), [(INSERT, ["new"], 1)]),
            (dict(old=1), Undefined, [(DELETE, ["old"], 1)]),
            (
                dict(same=1, old=2),
                dict(same=1, new1=3, new2=4),
                [(INSERT, ["new1"], 3), (INSERT, ["new2"], 4), (DELETE, ["old"], 2)],
            ),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_nested_dict(self):
        tests = [
            (dict(key=dict(same=None)), dict(key=dict(same=None)), []),
            (dict(key=dict()), dict(key=dict(added=None)), [(INSERT, ["key", "added"], None)]),
            (dict(key=dict(removed=None)), dict(key=dict()), [(DELETE, ["key", "removed"], None)]),
        ]
        for d1, d2, expected in tests:
            assert diff(d1, d2) == expected

    def test_diff_str_unicode_keys(self):
        d1 = {"old": "old", "same1": "same1", "same2": "same2"}
        d2 = {"new": "new", "same1": "same1", "same2": "same2"}
        assert diff(d1, d2) == [(INSERT, ["new"], "new"), (DELETE, ["old"], "old")]

    def test_diff_errors(self):
        tests = [("foo", True), ((1, 2), (3, 4)), (dict(key=(1, 2)), dict()), (None, [1, 2])]
        for d1, d2 in tests:
            with pytest.raises(TypeError):
                diff(d1, d2)

    def test_make_text_diff_empty(self):
        for got in make_text_diff([]):
            assert got == ""

    def test_make_text_diff_none(self):
        tests = [([(INSERT, [], None)], "+ None"), ([(DELETE, [], None)], "- None")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_bool(self):
        tests = [([(INSERT, [], True)], "+ True"), ([(DELETE, [], False)], "- False")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_int(self):
        tests = [([(INSERT, [], 123)], "+ 123"), ([(DELETE, [], 321)], "- 321")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_float(self):
        tests = [([(INSERT, [], 1.2)], "+ 1.2"), ([(DELETE, [], 3.4)], "- 3.4")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_unicode(self):
        tests = [([(INSERT, [], "new value")], "+ new value"), ([(DELETE, [], "old value")], "- old value")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_list(self):
        tests = [([(INSERT, [], [1, 2, 3])], "+ [1, 2, 3]"), ([(DELETE, [], [4, 5])], "- [4, 5]")]
        self._test_make_text_diff(tests)

    def test_make_text_diff_one_key(self):
        tests = [
            ([(INSERT, ["key"], "new value")], "+ key: new value"),
            ([(DELETE, ["key"], "old value")], "- key: old value"),
        ]
        self._test_make_text_diff(tests)

    def test_make_text_diff_multiple_keys(self):
        tests = [
            ([(INSERT, ["key1", "key2"], 1)], "+ key1.key2: 1"),
            ([(DELETE, ["key1", "key2", "key3"], 2)], "- key1.key2.key3: 2"),
        ]
        self._test_make_text_diff(tests)
