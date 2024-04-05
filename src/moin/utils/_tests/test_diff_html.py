# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.utils.diff_html Tests
"""


from moin.utils import diff_html


def test_indent():
    # input text
    test_input = """ \n


AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
"""
    # expeted result
    expected = """&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
"""
    result = diff_html.indent(test_input)
    assert result == expected


def test_diff():
    test_input1 = """ \n


AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
"""

    # Case 1: charobj.ratio() < 0.5 i.e. Insufficient similarity
    test_input2 = """ \n

BBB 006
BBB 007
BBB 008
BBB 009
BBB 100
"""
    result = diff_html.diff(test_input1, test_input2)
    expected = [
        (
            4,
            "<span><br>AAA 001<br>AAA 002<br>AAA 003<br>AAA 004<br>AAA 005</span>",
            4,
            "<span>BBB 006<br>BBB 007<br>BBB 008<br>BBB 009<br>BBB 100</span>",
        )
    ]
    assert result == expected

    # Case 2 : charobj.ratio() > 0.5 i.e. Some similarities
    test_input3 = """ \n

AAA 006
AAA 007
AAA 008
AAA 009
AAA 100
"""
    result = diff_html.diff(test_input1, test_input3)
    expected = [
        (
            4,
            "<br>AAA 00<span>1</span><br>AAA 00<span>2</span><br>AAA 00<span>3</span><br>AAA 00<span>4<br>AAA 005</span>",
            4,
            "<span>AAA 006</span><br>AAA 00<span>7</span><br>AAA 00<span>8</span><br>AAA 00<span>9</span><br>AAA <span>1</span>00",
        )
    ]
    assert result == expected
