# Copyright: 2019 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.utils Tests
"""


from moin.utils import show_time


class TestShowTime(object):

    def test_showTime(self):
        """ test somewhat arbitrary duration results """
        seconds_expected = ((25, ('seconds', 25)),
                            (89, ('seconds', 89)),
                            (91, ('minutes', 2)),
                            (5399, ('minutes', 90)),
                            (5401, ('hours', 2)),
                            (128999, ('hours', 36)),
                            (864000, ('weeks', 1)),
                            (4838399, ('weeks', 8)),
                            (4838401, ('months', 2)),
                            (63071999, ('months', 24)),
                            (126144000, ('years', 4)),
        )

        for seconds, expected in seconds_expected:
            result = show_time.duration(seconds)
            assert result == expected


coverage_modules = ['moin.utils.show_time']
