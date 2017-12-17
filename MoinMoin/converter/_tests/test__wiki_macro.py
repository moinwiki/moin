# Copyright: 2008 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter._wiki_macro
"""


import re

from MoinMoin.converter._args import Arguments
from MoinMoin.util.tree import xlink

from MoinMoin.converter._wiki_macro import *


class TestConverter(object):
    namespaces = {
        moin_page.namespace: '',
        xinclude.namespace: 'xi',
        xlink.namespace: 'xlink',
    }

    output_re = re.compile(r'(\s+xmlns(:\w+)?="[^"]+"|xmlns\(\w+=[^)]+\)\s+)')

    def setup_class(self):
        self.conv = ConverterMacro()

    def test_macro(self):
        data = [
            ('Macro', None, 'text',
                '<part alt="text" content-type="x-moin/macro;name=Macro" />',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" />'),
            ('Macro', u'arg1', 'text',
                '<part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1</arguments></part>',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1</arguments></inline-part>'),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def test_macro_arguments(self):
        data = [
            ('Macro', None, 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" />'),
            ('Macro', u'arg1,arg2', 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1,arg2</arguments></inline-part>'),
            ('Macro', 'key=value', 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>key=value</arguments></inline-part>'),
            ('Macro', u'arg1,arg2,key=value', 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments>arg1,arg2,key=value</arguments></inline-part>'),
        ]
        for name, args, text, output in data:
            yield (self._do, name, args, text, False, output)

    def test_pseudomacro(self):
        data = [
            ('BR', None, 'text',
                None,
                '<line-break />'),
            ('FootNote', u'note', 'text',
                '<p><note note-class="footnote"><note-body>note</note-body></note></p>',
                '<note note-class="footnote"><note-body>note</note-body></note>'),
            ('TableOfContents', None, 'text',
                '<table-of-content />',
                'text'),
            ('Include', u'page', 'text',
                '<div class="moin-p"><xi:include xi:href="wiki.local:page" /></div>',
                '<xi:include xi:href="wiki.local:page" />'),
            ('Include', u'^page', 'text',
                '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page))" /></div>',
                '<xi:include xi:xpointer="page:include(pages(^^page))" />'),
            # each Include macro performs its own parsing as needed
            ('Include', u'^page, sort=ascending', 'text',
                '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) sort(ascending))" /></div>',
                '<xi:include xi:xpointer="page:include(pages(^^page) sort(ascending))" />'),
            ('Include', u'^page, sort=descending', 'text',
                '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) sort(descending))" /></div>',
                '<xi:include xi:xpointer="page:include(pages(^^page) sort(descending))" />'),
            ('Include', u'^page, items=5', 'text',
                '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) items(5))" /></div>',
                '<xi:include xi:xpointer="page:include(pages(^^page) items(5))" />'),
            ('Include', u'^page, skipitems=5', 'text',
                '<div class="moin-p"><xi:include xi:xpointer="page:include(pages(^^page) skipitems(5))" /></div>',
                '<xi:include xi:xpointer="page:include(pages(^^page) skipitems(5))" />'),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def test_parser(self):
        data = [
            ('test', None, ('text', ),
                '<part content-type="x-moin/format;name=test"><body>text</body></part>'),
            # this form works, but is no longer used
            ('test', Arguments([u'arg1']), ('text', ),
                '<part content-type="x-moin/format;name=test"><arguments><argument>arg1</argument></arguments><body>text</body></part>'),
        ]
        for name, args, text, output in data:
            yield (self._do_parser, name, args, text, output)

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def _do(self, name, args, text, context_block, output):
        result = self.conv.macro(name, args, text, context_block)
        if output is not None or result is not None:
            if isinstance(result, basestring):
                assert result == output
            else:
                assert self.serialize(result) == output

    def _do_parser(self, name, args, text, output):
        result = self.conv.parser(name, args, text)
        if output is not None or result is not None:
            assert self.serialize(result) == output
