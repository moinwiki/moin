# Copyright: 2007 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.utils.
"""

import pytest

from moin import utils


class TestUtil:

    @pytest.mark.parametrize(
        "input1, input2, expected",
        [
            ([], [], True),
            (["x"], ["x", "x"], True),
            (["one", "two", "three"], ["two", "one", "three"], True),
            (["x"], ["y"], False),
            (["x"], ["x", "y"], False),
        ],
    )
    def test_contain_identical_values(self, input1: list[str], input2: list[str], expected: bool):
        assert expected == utils.contain_identical_values(input1, input2)

    @pytest.mark.parametrize(
        "input, expected",
        [
            ("", []),
            (" hello ,, ,", ["hello"]),
            ("abc, def ", ["abc", "def"]),
            ("red, green, purple, red", ["red", "green", "purple"]),
        ],
    )
    def test_split_string(self, input: str, expected: list[str]):
        assert expected == utils.split_string(input)

    def test_rangelist(self):
        """utils.rangelist: test correct behavior for various input values"""
        result = utils.rangelist([])
        expected = ""
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([42])
        expected = "42"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([42, 23])
        expected = "23,42"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([1, 2, 3, 4, 5])
        expected = "1-5"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([2, 5, 3])
        expected = "2-3,5"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([2, 3, 5, 6])
        expected = "2-3,5-6"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()

        result = utils.rangelist([2, 3, 5, 6, 23, 100, 101, 102, 104])
        expected = "2-3,5-6,23,100-102,104"
        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()


coverage_modules = ["moin.utils"]
