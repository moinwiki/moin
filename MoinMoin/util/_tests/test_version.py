"""
    MoinMoin - MoinMoin.version Tests

    @copyright: 2010 by MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.util.version import Version


class TestVersion(object):
    def test_Version(self):
        # test properties
        assert Version(1, 2, 3).major == 1
        assert Version(1, 2, 3).minor == 2
        assert Version(1, 2, 3).release == 3
        assert Version(1, 2, 3, 'a4').additional == 'a4'
        # test Version init and Version to str conversion
        assert str(Version(1)) == "1.0.0"
        assert str(Version(1, 2)) == "1.2.0"
        assert str(Version(1, 2, 3)) == "1.2.3"
        assert str(Version(1, 2, 3, 'a4')) == "1.2.3a4"
        assert str(Version(version='1.2.3')) == "1.2.3"
        assert str(Version(version='1.2.3a4')) == "1.2.3a4"
        # test Version comparison, trivial cases
        assert Version() == Version()
        assert Version(1) == Version(1)
        assert Version(1, 2) == Version(1, 2)
        assert Version(1, 2, 3) == Version(1, 2, 3)
        assert Version(1, 2, 3, 'a4') == Version(1, 2, 3, 'a4')
        assert Version(1) != Version(2)
        assert Version(1, 2) != Version(1, 3)
        assert Version(1, 2, 3) != Version(1, 2, 4)
        assert Version(1, 2, 3, 'a4') != Version(1, 2, 3, 'a5')
        assert Version(1) < Version(2)
        assert Version(1, 2) < Version(1, 3)
        assert Version(1, 2, 3) < Version(1, 2, 4)
        assert Version(1, 2, 3, 'a4') < Version(1, 2, 3, 'a5')
        assert Version(1, 2, 3, 'b4') < Version(1, 2, 3, 'b5')
        assert Version(1, 2, 3, 'c4') < Version(1, 2, 3, 'c5')
        assert Version(2) > Version(1)
        assert Version(1, 3) > Version(1, 2)
        assert Version(1, 2, 4) > Version(1, 2, 3)
        assert Version(1, 2, 3, 'b1') > Version(1, 2, 3, 'a1')
        assert Version(1, 2, 3, 'c1') > Version(1, 2, 3, 'b1')
        # test Version comparison, more delicate cases
        assert Version(1, 2, 3) > Version(1, 2, 3, 'c1')
        assert Version(1, 12) > Version(1, 9)
        assert Version(1, 12) > Version(1, 1, 2)
        # test Version playing nice with tuples
        assert Version(1, 2, 3) < (1, 2, 4)
        assert Version(1, 2, 3, 'c99') < (1, 2, 4)
        assert Version(1, 2, 4) > (1, 2, 3)
        assert Version(1, 2, 4) > (1, 2, 3, 'c99')


coverage_modules = ['MoinMoin.util.version']
