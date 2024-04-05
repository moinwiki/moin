# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters._wiki_macro
"""

import pytest

from . import serialize, XMLNS_RE2

from moin.utils.tree import moin_page, xlink, xinclude
from moin.converters._wiki_macro import ConverterMacro
from moin.converters._args import Arguments


class TestConverter:
    namespaces = {moin_page.namespace: "", xinclude.namespace: "xi", xlink.namespace: "xlink"}

    output_re = XMLNS_RE2

    def setup_class(self):
        self.conv = ConverterMacro()

    data = [
        (
            "Macro",
            None,
            "text",
            '<part alt="text" content-type="x-moin/macro;name=Macro" />',
            '<inline-part alt="text" content-type="x-moin/macro;name=Macro" />',
        ),
        (
            "Macro",
            "arg1",
            "text",
            '<part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1</arguments></part>',
            '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1</arguments></inline-part>',
        ),
    ]

    @pytest.mark.parametrize("name,args,text,output_block,output_inline", data)
    def test_macro(self, name, args, text, output_block, output_inline):
        self._do(name, args, text, True, output_block)
        self._do(name, args, text, False, output_inline)

    data = [
        ("Macro", None, "text", '<inline-part alt="text" content-type="x-moin/macro;name=Macro" />'),
        (
            "Macro",
            "arg1,arg2",
            "text",
            '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1,arg2</arguments></inline-part>',
        ),
        (
            "Macro",
            "key=value",
            "text",
            '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>key=value</arguments></inline-part>',
        ),
        (
            "Macro",
            "arg1,arg2,key=value",
            "text",
            '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1,arg2,key=value</arguments></inline-part>',
        ),
    ]

    @pytest.mark.parametrize("name,args,text,output", data)
    def test_macro_arguments(self, name, args, text, output):
        self._do(name, args, text, False, output)

    data = [
        ("BR", None, "text", None, "<line-break />"),
        (
            "FootNote",
            "note",
            "text",
            '<p><note note-class="footnote"><note-body>note</note-body></note></p>',
            '<note note-class="footnote"><note-body>note</note-body></note>',
        ),
        ("TableOfContents", None, "text", "<table-of-content />", "text"),
        (
            "Include",
            "page",
            "text",
            '<div class="moin-p"><xi:include xi:href="wiki.local:page" /></div>',
            '<xi:include xi:href="wiki.local:page" />',
        ),
        (
            "Include",
            "^page",
            "text",
            '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page))" /></div>',
            '<xi:include xi:xpointer="page:include(pages(^^page))" />',
        ),
        # each Include macro performs its own parsing as needed
        (
            "Include",
            "^page, sort=ascending",
            "text",
            '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) sort(ascending))" /></div>',
            '<xi:include xi:xpointer="page:include(pages(^^page) sort(ascending))" />',
        ),
        (
            "Include",
            "^page, sort=descending",
            "text",
            '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) sort(descending))" /></div>',
            '<xi:include xi:xpointer="page:include(pages(^^page) sort(descending))" />',
        ),
        (
            "Include",
            "^page, items=5",
            "text",
            '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) items(5))" /></div>',
            '<xi:include xi:xpointer="page:include(pages(^^page) items(5))" />',
        ),
        (
            "Include",
            "^page, skipitems=5",
            "text",
            '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) skipitems(5))" /></div>',
            '<xi:include xi:xpointer="page:include(pages(^^page) skipitems(5))" />',
        ),
    ]

    @pytest.mark.parametrize("name,args,text,output_block,output_inline", data)
    def test_pseudomacro(self, name, args, text, output_block, output_inline):
        self._do(name, args, text, True, output_block)
        self._do(name, args, text, False, output_inline)

    data = [
        ("test", None, ("text",), '<part content-type="x-moin/format;name=test"><body>text</body></part>'),
        # this form works, but is no longer used
        (
            "test",
            Arguments(["arg1"]),
            ("text",),
            '<part content-type="x-moin/format;name=test"><arguments><argument>arg1</argument></arguments><body>text</body></part>',
        ),
    ]

    @pytest.mark.parametrize("name,args,text,output", data)
    def test_parser(self, name, args, text, output):
        self._do_parser(name, args, text, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def _do(self, name, args, text, context_block, output):
        result = self.conv.macro(name, args, text, context_block)
        if output is not None or result is not None:
            if not isinstance(result, str):
                result = self.serialize_strip(result)
            assert result == output

    def _do_parser(self, name, args, text, output):
        result = self.conv.parser(name, args, text)
        if output is not None or result is not None:
            result = self.serialize_strip(result)
            assert result == output
