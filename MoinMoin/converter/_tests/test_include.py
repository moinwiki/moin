"""
MoinMoin - Tests for MoinMoin.converter.include

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

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

