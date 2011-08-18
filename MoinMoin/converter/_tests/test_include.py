# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.include
"""


import pytest

from MoinMoin.converter.include import *

def test_XPointer():
    x = XPointer('a')
    assert len(x) == 1
    e = x[0]
    assert e.name == 'a'
    assert e.data is None

    x = XPointer('a(b)')
    assert len(x) == 1
    e = x[0]
    assert e.name == 'a'
    assert e.data == 'b'

    x = XPointer('a(^(b^)^^)')
    assert len(x) == 1
    e = x[0]
    assert e.name == 'a'
    assert e.data == '^(b^)^^'
    assert e.data_unescape == '(b)^'

    x = XPointer('a(b)c(d)')
    assert len(x) == 2
    e = x[0]
    assert e.name == 'a'
    assert e.data == 'b'
    e = x[1]
    assert e.name == 'c'
    assert e.data == 'd'

    x = XPointer('a(b) c(d)')
    assert len(x) == 2
    e = x[0]
    assert e.name == 'a'
    assert e.data == 'b'
    e = x[1]
    assert e.name == 'c'
    assert e.data == 'd'
    
    x = XPointer('a(a(b))')
    assert len(x) == 1
    e = x[0]
    assert e.name == 'a'
    assert e.data == 'a(b)'

