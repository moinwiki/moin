"""
MoinMoin - Tests for MoinMoin.macro._base

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import py.test
py.test.skip("test is out of sync with tested code")

from MoinMoin.macro._base import *

def test_MacroBase___init__():
    request = object()

    m = MacroBase(request, None, 'alt', 'context')

    assert m.immutable is False
    assert m.alt == 'alt'
    assert m.context == 'context'

def test_MacroBlockBase___call__():
    item = u'text'

    class Test(MacroBlockBase):
        def call_macro(self, content):
            return item

    r = Test(None, None, 'alt', 'block')()
    assert r is item

    r = Test(None, None, 'alt', 'inline')()
    assert r == 'alt'

def test_MacroInlineBase___call__():
    item = u'text'

    class Test(MacroInlineBase):
        def call_macro(self, content):
            return item

    r = Test(None, None, 'alt', 'block')()
    assert r[0] is item

    r = Test(None, None, 'alt', 'inline')()
    assert r is item

def test_MacroInlineOnlyBase___call__():
    item = u'text'

    class Test(MacroInlineOnlyBase):
        def call_macro(self, content):
            return item

    r = Test(None, None, 'alt', 'block')()
    assert r is None

    r = Test(None, None, 'alt', 'inline')()
    assert r is item

