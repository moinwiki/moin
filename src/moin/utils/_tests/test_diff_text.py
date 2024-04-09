# Copyright: 2007 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils.diff_text Tests
"""


from moin.utils import diff_text


class TestDiffText:

    def testDiff(self):
        """utils.diff_text.diff: test correct diff calculation"""
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

        result = diff_text.diff(in1.splitlines(), in2.splitlines())
        result = "\n".join(result)

        expected = """\
  AAA 001
  AAA 002
- AAA 003
- AAA 004
  AAA 005
  AAA 006
  AAA 007
  AAA 008
+ BBB 001
+ BBB 002
  AAA 009
  AAA 010
+ BBB 003
- AAA 011
- AAA 012
- AAA 013
- AAA 014"""

        assert result == expected, 'Expected "%(expected)s" but got "%(result)s"' % locals()


coverage_modules = ["moin.utils.diff_text"]
