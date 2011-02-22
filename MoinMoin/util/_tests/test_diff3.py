# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.util.diff3 Tests

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import diff3

class TestDiff3:

    def testTextMerge(self):
        """ util.diff3.text_merge: test correct merging """
        in1 = """AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
AAA 006
AAA 007
AAA 008
AAA 009
AAA 010
AAA 011
AAA 012
AAA 013
AAA 014
"""

        in2 = """AAA 001
AAA 002
AAA 005
AAA 006
AAA 007
AAA 008
BBB 001
BBB 002
AAA 009
AAA 010
BBB 003
"""

        in3 = """AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
AAA 006
AAA 007
AAA 008
CCC 001
CCC 002
CCC 003
AAA 012
AAA 013
AAA 014
"""
        result = diff3.text_merge(in1, in2, in3)

        expected = """AAA 001
AAA 002
AAA 005
AAA 006
AAA 007
AAA 008
<<<<<<<<<<<<<<<<<<<<<<<<<
BBB 001
BBB 002
AAA 009
AAA 010
BBB 003
=========================
CCC 001
CCC 002
CCC 003
AAA 012
AAA 013
AAA 014
>>>>>>>>>>>>>>>>>>>>>>>>>
"""
        assert result == expected, ('Expected "%(expected)s" but got "%(result)s"') % locals()


coverage_modules = ['MoinMoin.util.diff3']

