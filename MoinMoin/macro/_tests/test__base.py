# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.macro._base
"""

import pytest
from MoinMoin.macro._base import *


class TestMacroBase(object):
    """ Test for Macro base and related classes """

    def test_MacroBase(self):
        """ test for MacroBase class """
        macrobase_obj = MacroBase()
        assert not macrobase_obj.immutable
        with pytest.raises(NotImplementedError):
            macrobase_obj.__call__('content', 'arguments', 'page_url', 'alternative', 'context_block')

    def test_MacroBlockBase(self):
        """ test for MacroBlockBase class """
        class Test_MacroBlockBase(MacroBlockBase):
            """ inherited class from MacroBlockBase """
            def __init__(self):
                self.alt = 'alt returned'

        macroblockbase_obj = Test_MacroBlockBase()
        result = macroblockbase_obj.__call__('content', 'arguments', 'page_url', 'alternative', context_block=False)
        assert result == 'alt returned'
        with pytest.raises(NotImplementedError):
            result = macroblockbase_obj.__call__('content', 'arguments', 'page_url', 'alternative', 'context_block')

    def test_MacroInlineBase(self):
        """ test for MacroInlineBase class """
        class Test_MacroInlineBase(MacroInlineBase):
            """ inherited class from MacroInlineBase """
            def macro(self, content, arguments, page_url, alternative):
                return 'test_macro'

        macroinlinebase_obj = Test_MacroInlineBase()
        result = macroinlinebase_obj.__call__('content', 'arguments', 'page_url', 'alternative', context_block=False)
        assert result == 'test_macro'
        result = macroinlinebase_obj.__call__('content', 'arguments', 'page_url', 'alternative', 'context_block')
        assert result.text == 'test_macro'
        result.remove('test_macro')
        assert not result.text

    def test_MacroInlineOnlyBase(self):
        """ test for MacroInlineOnlyBase class """
        class Test_MacroInlineOnlyBase(MacroInlineOnlyBase):
            """ inherited class from MacroInlineOnlyBase """
            def macro(self, content, arguments, page_url, alternative):
                return 'test_macro'

        macroinlineonlybase_obj = Test_MacroInlineOnlyBase()
        result = macroinlineonlybase_obj.__call__('content', 'arguments', 'page_url', 'alternative', context_block=False)
        assert result == 'test_macro'
