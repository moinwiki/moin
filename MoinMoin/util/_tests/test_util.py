# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.util Tests

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import util

class TestUtil:

    def testRangeList(self):
        """ util.rangelist: test correct function for misc. input values """
        result = util.rangelist([])
        expected = ''
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([42])
        expected = '42'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([42, 23])
        expected = '23,42'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([1, 2, 3, 4, 5])
        expected = '1-5'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([2, 5, 3])
        expected = '2-3,5'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([2, 3, 5, 6])
        expected = '2-3,5-6'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

        result = util.rangelist([2, 3, 5, 6, 23, 100, 101, 102, 104])
        expected = '2-3,5-6,23,100-102,104'
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()

    def testRandomString(self):
        """ util.random_string: test randomness and length """
        length = 8
        result1 = util.random_string(length)
        result2 = util.random_string(length)
        assert result1 != result2, ('Expected different random strings, but got "%(result1)s" and "%(result2)s"') % locals()

        result = len(util.random_string(length))
        expected = length
        assert result == expected, ('Expected length "%(expected)s" but got "%(result)s"') % locals()

coverage_modules = ['MoinMoin.util']
