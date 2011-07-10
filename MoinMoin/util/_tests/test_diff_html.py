# -*- coding: utf-8 -*-
# Copyright: 2011 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.diff_html Tests
"""

import pytest
from MoinMoin.util import diff_html

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
    test_input = """ \n


AAA 001
AAA 002
AAA 003
AAA 004
AAA 005
"""
    result = diff_html.diff(test_input, 'asdf')
    expected = [(1, '<span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;AAA 001<br>AAA 002<br>AAA 003<br>AAA 004<br>AAA 005</span>', 
                 1, '<span>asdf</span>')]    
    assert result == expected
                         
