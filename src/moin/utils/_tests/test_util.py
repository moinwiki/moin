# Copyright: 2007 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils Tests
"""


from moin import utils


class TestUtil:

    def testRangeList(self):
        """utils.rangelist: test correct function for misc. input values"""
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
