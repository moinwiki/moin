"""
MoinMoin - Tests for MoinMoin.converter.creole_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import py.test

import re

from MoinMoin.util.tree import moin_page, xlink

from ..creole_in import Converter


class TestConverter(object):
    namespaces = {
        moin_page: '',
        xlink: 'xlink',
    }

    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            (u'Text',
                '<page><body><p>Text</p></body></page>'),
            (u'Text\nTest',
                '<page><body><p>Text\nTest</p></body></page>'),
            (u'Text\n\nTest',
                '<page><body><p>Text</p><p>Test</p></body></page>'),
            (u'Line\\\\Break',
                '<page><body><p>Line<line-break />Break</p></body></page>'),
            (u'Line\\\\\nBreak',
                '<page><body><p>Line<line-break />\nBreak</p></body></page>'),
            (u'http://moinmo.in/',
                '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>'),
            (u'[[http://moinmo.in/]]',
                '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>'),
            (u'[[http://moinmo.in/|MoinMoin]]',
                '<page><body><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></body></page>'),
            (u'[[MoinMoin]]',
                '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
            (u'{{http://moinmo.in/}}',
                '<page><body><p><object xlink:href="http://moinmo.in/">http://moinmo.in/</object></p></body></page>'),
            (u'{{http://moinmo.in/|MoinMoin}}',
                '<page><body><p><object xlink:href="http://moinmo.in/">MoinMoin</object></p></body></page>'),
            (u'----',
                '<page><body><separator /></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_args(self):
        from MoinMoin.converter._args import Arguments
        from MoinMoin.util.iri import Iri
        data = [
            (u'Text',
                '<page><body style="background-color: red"><p>Text</p></body></page>',
                {'arguments': Arguments(keyword={'style': 'background-color: red'})}),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_emphasis(self):
        data = [
            (u'//Emphasis//',
                '<page><body><p><emphasis>Emphasis</emphasis></p></body></page>'),
            (u'**Strong**',
                '<page><body><p><strong>Strong</strong></p></body></page>'),
            (u'//**Both**//',
                '<page><body><p><emphasis><strong>Both</strong></emphasis></p></body></page>'),
            (u'**//Both//**',
                '<page><body><p><strong><emphasis>Both</emphasis></strong></p></body></page>'),
            (u'Text //Emphasis\n//Text',
                '<page><body><p>Text <emphasis>Emphasis\n</emphasis>Text</p></body></page>'),
            (u'Text //Emphasis\n\nText',
                '<page><body><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_escape(self):
        data = [
            (u'~http://moinmo.in/',
                '<page><body><p>http://moinmo.in/</p></body></page>'),
            (u'~[[escape]]',
                '<page><body><p>[[escape]]</p></body></page>'),
            (u'~<<escape>>',
                '<page><body><p>&lt;&lt;escape&gt;&gt;</p></body></page>'),
            (u'~{~{{escape}}}',
                '<page><body><p>{{{escape}}}</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_heading(self):
        data = [
            (u'= Heading 1',
                '<page><body><h outline-level="1">Heading 1</h></body></page>'),
            (u'== Heading 2',
                '<page><body><h outline-level="2">Heading 2</h></body></page>'),
            (u'=== Heading 3',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
            (u'==== Heading 4',
                '<page><body><h outline-level="4">Heading 4</h></body></page>'),
            (u'===== Heading 5',
                '<page><body><h outline-level="5">Heading 5</h></body></page>'),
            (u'====== Heading 6',
                '<page><body><h outline-level="6">Heading 6</h></body></page>'),
            (u'= Heading 1 =',
                '<page><body><h outline-level="1">Heading 1</h></body></page>'),
            (u'== Heading 2 ==',
                '<page><body><h outline-level="2">Heading 2</h></body></page>'),
            (u'=== Heading 3 ===',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
            (u'==== Heading 4 ====',
                '<page><body><h outline-level="4">Heading 4</h></body></page>'),
            (u'===== Heading 5 =====',
                '<page><body><h outline-level="5">Heading 5</h></body></page>'),
            (u'====== Heading 6 ======',
                '<page><body><h outline-level="6">Heading 6</h></body></page>'),
            (u'=== Heading 3',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
            (u'=== Heading 3 =',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
            (u'=== Heading 3 ==',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u'* Item',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u' *Item',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u'*Item',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u'* Item\nItem',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></body></page>'),
            (u'* Item 1\n*Item 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>'),
            (u'* Item 1\n** Item 1.2\n* Item 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>'),
            (u'* List 1\n\n* List 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>'),
            (u'# Item',
                '<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u'* List 1\n# List 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="ordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macro(self):
        data = [
            (u'<<BR>>',
                '<page><body /></page>'),
            (u'Text<<BR>>Text',
                '<page><body><p>Text<line-break />Text</p></body></page>'),
            (u'<<Macro>>',
                '<page><body><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u'<<Macro(arg)>>',
                '<page><body><part alt="&lt;&lt;Macro(arg)&gt;&gt;" content-type="x-moin/macro;name=Macro"><arguments><argument>arg</argument></arguments></part></body></page>'),
            (u' <<Macro>> ',
                '<page><body><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u'Text <<Macro>>',
                '<page><body><p>Text <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>'),
            (u'Text <<Macro(arg)>>',
                '<page><body><p>Text <inline-part alt="&lt;&lt;Macro(arg)&gt;&gt;" content-type="x-moin/macro;name=Macro"><arguments><argument>arg</argument></arguments></inline-part></p></body></page>'),
            (u'Text\n<<Macro>>',
                '<page><body><p>Text</p><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u'Text\nText <<Macro>>',
                '<page><body><p>Text\nText <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>'),
            (u'Text\n\n<<Macro>>',
                '<page><body><p>Text</p><part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u'|Cell',
                '<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>'),
            (u'|Cell|',
                '<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>'),
            (u'|Cell 1|Cell 2',
                '<page><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>'),
            (u'|Cell 1|Cell 2|',
                '<page><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>'),
            (u'|Row 1\n|Row 2\n',
                '<page><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>'),
            (u'|Row 1|\n|Row 2|\n',
                '<page><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>'),
            (u'|Cell 1.1|Cell 1.2|\n|Cell 2.1|Cell 2.2|\n',
                '<page><body><table><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_nowiki(self):
        data = [
            (u'{{{nowiki}}}',
                '<page><body><p><code>nowiki</code></p></body></page>'),
            (u'{{{{nowiki}}}}',
                '<page><body><p><code>{nowiki}</code></p></body></page>'),
            (u'text: {{{nowiki}}}, text',
                '<page><body><p>text: <code>nowiki</code>, text</p></body></page>'),
            (u'{{{\nnowiki\n}}}',
                '<page><body><blockcode>nowiki</blockcode></body></page>'),
            (u'{{{\nnowiki\nno\nwiki\n}}}',
                '<page><body><blockcode>nowiki\nno\nwiki</blockcode></body></page>'),
            (u'{{{nowiki}}} {{{nowiki}}}',
                '<page><body><p><code>nowiki</code> <code>nowiki</code></p></body></page>'),
            # XXX: Is <page> correct?
            (u'{{{\n#!\nwiki\n}}}',
               '<page><body><page><body><p>wiki</p></body></page></body></page>'),
            (u'{{{\n#!(style="background-color: red")\nwiki\n}}}',
               '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>'),
            (u'{{{\n#!creole\nwiki\n}}}',
               '<page><body><page><body><p>wiki</p></body></page></body></page>'),
            (u'{{{\n#!creole(style="background-color: red")\nwiki\n}}}',
               '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>'),
            (u'{{{\n#!text/plain\ntext\n}}}',
               u'<page><body><part content-type="text/plain"><body>text</body></part></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_composite(self):
        data = [
            (u'Text\n* Item\n\nText',
                '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>'),
            (u'Text\n* Item\n= Heading',
                '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><h outline-level="1">Heading</h></body></page>'),
            (u'Text\n* Item\n{{{\nnowiki\n}}}',
                '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><blockcode>nowiki</blockcode></body></page>'),
            (u'Text\n* Item\n|Item',
                '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table></body></page>'),
            (u'Text\n|Item\nText',
                '<page><body><p>Text</p><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}):
        out = self.conv(input.split(u'\n'), **args)
        assert self.serialize(out) == output

