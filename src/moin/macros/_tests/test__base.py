# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - tests for moin.macros._base.
"""

import pytest
from moin.macros._base import MacroBase, MacroBlockBase, MacroInlineBase, MacroInlineOnlyBase, MacroPageLinkListBase
from moin.utils.tree import html


class TestMacroBase:
    """Tests for macro base and related classes."""

    def test_MacroBase(self):
        """Test MacroBase class."""
        macrobase_obj = MacroBase()
        assert not macrobase_obj.immutable
        with pytest.raises(NotImplementedError):
            macrobase_obj.__call__("content", "arguments", "page_url", "alternative", "context_block")

    def test_MacroBlockBase(self):
        """Test MacroBlockBase class."""

        class Test_MacroBlockBase(MacroBlockBase):
            """Subclass of MacroBlockBase."""

        macroblockbase_obj = Test_MacroBlockBase()
        result = macroblockbase_obj.__call__("content", "arguments", "page_url", "alternative", context_block=False)
        assert "error" in result.attrib[html.class_]
        with pytest.raises(NotImplementedError):
            macroblockbase_obj.__call__("content", "arguments", "page_url", "alternative", "context_block")

    def test_MacroInlineBase(self):
        """Test MacroInlineBase class."""

        class Test_MacroInlineBase(MacroInlineBase):
            """Subclass of MacroInlineBase."""

            def macro(self, content, arguments, page_url, alternative):
                return "test_macro"

        macroinlinebase_obj = Test_MacroInlineBase()
        result = macroinlinebase_obj.__call__("content", "arguments", "page_url", "alternative", context_block=False)
        assert result == "test_macro"
        result = macroinlinebase_obj.__call__("content", "arguments", "page_url", "alternative", "context_block")
        assert result.text == "test_macro"
        result.remove("test_macro")
        assert not result.text

    def test_MacroInlineOnlyBase(self):
        """Test MacroInlineOnlyBase class."""

        class Test_MacroInlineOnlyBase(MacroInlineOnlyBase):
            """Subclass of MacroInlineOnlyBase."""

            def macro(self, content, arguments, page_url, alternative):
                return "test_macro"

        macroinlineonlybase_obj = Test_MacroInlineOnlyBase()
        result = macroinlineonlybase_obj.__call__(
            "content", "arguments", "page_url", "alternative", context_block=False
        )
        assert result == "test_macro"

    def test_MacroPageLinkListBase(self):
        """Test MacroPageLinkListBase class."""

        class Test_MacroPageLinkListBase(MacroPageLinkListBase):
            """Subclass of MacroPageLinkListBase."""

            def macro(self, content, arguments, page_url, alternative):
                return "test_macro"

        macropagelinklistbase_obj = Test_MacroPageLinkListBase()
        result = macropagelinklistbase_obj.__call__("content", "arguments", "page_url", "alternative", "context_block")
        assert result == "test_macro"
