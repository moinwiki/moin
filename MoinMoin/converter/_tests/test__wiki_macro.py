"""
MoinMoin - Tests for MoinMoin.converter._wiki_macro

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import py.test
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
            ('Macro', Arguments([u'arg1']), 'text',
                '<part alt="text" content-type="x-moin/macro;name=Macro"><arguments><argument>arg1</argument></arguments></part>',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments><argument>arg1</argument></arguments></inline-part>'),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def test_macro_arguments(self):
        data = [
            ('Macro', None, 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" />'),
            ('Macro', Arguments([u'arg1', u'arg2']), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments><argument>arg1</argument><argument>arg2</argument></arguments></inline-part>'),
            ('Macro', Arguments([], {'key': 'value'}), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments><argument name="key">value</argument></arguments></inline-part>'),
            ('Macro', Arguments([u'arg1', u'arg2'], {'key': 'value'}), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro"><arguments><argument>arg1</argument><argument>arg2</argument><argument name="key">value</argument></arguments></inline-part>'),
        ]
        for name, args, text, output in data:
            yield (self._do, name, args, text, False, output)

    def test_pseudomacro(self):
        data = [
            ('BR', None, 'text',
                None,
                '<line-break />'),
            ('FootNote', Arguments([u'note']), 'text',
                '<p><note note-class="footnote"><note-body>note</note-body></note></p>',
                '<note note-class="footnote"><note-body>note</note-body></note>'),
            ('TableOfContents', None, 'text',
                '<table-of-content />',
                'text'),
            ('Include', Arguments([u'page']), 'text',
                '<xi:include xi:href="wiki.local:page" />',
                'text'),
            ('Include', Arguments([u'^page']), 'text',
                '<xi:include xi:xpointer="page:include(pages(^^page))" />',
                'text'),
            ('Include', Arguments([u'^page'], {u'sort': u'ascending'}), 'text',
                '<xi:include xi:xpointer="page:include(pages(^^page) sort(ascending))" />',
                'text'),
            ('Include', Arguments([u'^page'], {u'sort': u'descending'}), 'text',
                '<xi:include xi:xpointer="page:include(pages(^^page) sort(descending))" />',
                'text'),
            ('Include', Arguments([u'^page'], {u'items': u'5'}), 'text',
                '<xi:include xi:xpointer="page:include(pages(^^page) items(5))" />',
                'text'),
            ('Include', Arguments([u'^page'], {u'skipitems': u'5'}), 'text',
                '<xi:include xi:xpointer="page:include(pages(^^page) skipitems(5))" />',
                'text'),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def test_parser(self):
        data = [
            ('test', None, ('text', ),
                '<part content-type="x-moin/format;name=test"><body>text</body></part>'),
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

