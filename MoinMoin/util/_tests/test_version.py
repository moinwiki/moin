# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.version Tests

    @copyright: 2010 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util.version import Version


class TestVersion(object):
    def test_Version(self):
        # test properties
        assert Version(1, 2, 3).major == 1
        assert Version(1, 2, 3).minor == 2
        assert Version(1, 2, 3).release == 3
        assert Version(1, 2, 3, '4.5alpha6').additional == '4.5alpha6'
        # test Version init and Version to str conversion
        assert str(Version(1)) == "1.0.0"
        assert str(Version(1, 2)) == "1.2.0"
        assert str(Version(1, 2, 3)) == "1.2.3"
        assert str(Version(1, 2, 3, '4.5alpha6')) == "1.2.3-4.5alpha6"
        assert str(Version(version='1.2.3')) == "1.2.3"
        assert str(Version(version='1.2.3-4.5alpha6')) == "1.2.3-4.5alpha6"
        # test Version comparison, trivial cases
        assert Version() == Version()
        assert Version(1) == Version(1)
        assert Version(1, 2) == Version(1, 2)
        assert Version(1, 2, 3) == Version(1, 2, 3)
        assert Version(1, 2, 3, 'foo') == Version(1, 2, 3, 'foo')
        assert Version(1) != Version(2)
        assert Version(1, 2) != Version(1, 3)
        assert Version(1, 2, 3) != Version(1, 2, 4)
        assert Version(1, 2, 3, 'foo') != Version(1, 2, 3, 'bar')
        assert Version(1) < Version(2)
        assert Version(1, 2) < Version(1, 3)
        assert Version(1, 2, 3) < Version(1, 2, 4)
        assert Version(1, 2, 3, 'bar') < Version(1, 2, 3, 'foo')
        assert Version(2) > Version(1)
        assert Version(1, 3) > Version(1, 2)
        assert Version(1, 2, 4) > Version(1, 2, 3)
        assert Version(1, 2, 3, 'foo') > Version(1, 2, 3, 'bar')
        # test Version comparison, more delicate cases
        assert Version(1, 12) > Version(1, 9)
        assert Version(1, 12) > Version(1, 1, 2)
        assert Version(1, 0, 0, '0.0a2') > Version(1, 0, 0, '0.0a1')
        assert Version(1, 0, 0, '0.0b1') > Version(1, 0, 0, '0.0a9')
        assert Version(1, 0, 0, '0.0b2') > Version(1, 0, 0, '0.0b1')
        assert Version(1, 0, 0, '0.0c1') > Version(1, 0, 0, '0.0b9')
        assert Version(1, 0, 0, '1') > Version(1, 0, 0, '0.0c9')
        # test Version playing nice with tuples
        assert Version(1, 2, 3) == (1, 2, 3, '')
        assert Version(1, 2, 4) > (1, 2, 3)


coverage_modules = ['MoinMoin.util.version']
