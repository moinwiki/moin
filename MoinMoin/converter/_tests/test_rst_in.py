# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.rst_in
"""


import re

from MoinMoin.converter.rst_in import *


class TestConverter(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
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
            (u'H\\ :sub:`2`\\ O\n\nE = mc\\ :sup:`2`', '<page><body><p>H<span baseline-shift="sub">2</span>O</p><p>E = mc<span baseline-shift="super">2</span></p></body></page>'),
            (u'| Lend us a couple of bob till Thursday.', '<page><body>Lend us a couple of bob till Thursday.</body></page>'),
            (u'**Text**', '<page><body><p><strong>Text</strong></p></body></page>'),
            (u'*Text*', '<page><body><p><emphasis>Text</emphasis></p></body></page>'),
            (u'``Text``', '<page><body><p><code>Text</code></p></body></page>'),
            (u"`Text <javascript:alert('xss')>`_", u'<page><body><p>Text</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u'1. a\n   b\n   c\n\n2. b\n\n   d', '''<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>a
b
c</p></list-item-body></list-item><list-item><list-item-body><p>b</p><p>d</p></list-item-body></list-item></list></body></page>'''),
            (u'1. a\n2. b\n\nA. c\n\na. A\n\n   3. B\n\n   4. C\n\n', '<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>a</p></list-item-body></list-item><list-item><list-item-body><p>b</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="upper-alpha"><list-item><list-item-body><p>c</p></list-item-body></list-item></list><list item-label-generate="ordered" list-style-type="lower-alpha"><list-item><list-item-body><p>A</p><list item-label-generate="ordered"><list-item><list-item-body><p>B</p></list-item-body></list-item><list-item><list-item-body><p>C</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>'),
            (u'* A\n\n   - B\n\n      + C\n\n   - D\n\n* E', '<page><body><list item-label-generate="unordered"><list-item><list-item-body><p>A</p><list><list-item><list-item-body><list item-label-generate="unordered"><list-item><list-item-body><p>B</p><list><list-item><list-item-body><list item-label-generate="unordered"><list-item><list-item-body><p>C</p></list-item-body></list-item></list></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>D</p></list-item-body></list-item></list></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>E</p></list-item-body></list-item></list></body></page>'),
            (u'what\n      def\n\nhow\n      to', '<page><body><list><list-item><list-item-label>what</list-item-label><list-item-body><p>def</p></list-item-body></list-item><list-item><list-item-label>how</list-item-label><list-item-body><p>to</p></list-item-body></list-item></list></body></page>')
            ]
        for i in data:
            yield (self.do, ) + i

    def test_image(self):
        data = [
            (u'.. image:: images/biohazard.png', '<page><body><object xlink:href="images/biohazard.png" /></body></page>'),
            (u""".. image:: images/biohazard.png
   :height: 100
   :width: 200
   :scale: 50
   :alt: alternate text""", '<page><body><object alt="images/biohazard.png" height="100" scale="50" width="200" xlink:href="images/biohazard.png" /></body></page>'),
            (u'abc |a| cba\n\n.. |a| image:: test.png', '<page><body><p>abc <object alt="test.png" xlink:href="test.png" /> cba</p></body></page>'),
            ]
        for i in data:
            yield (self.do, ) + i

    def test_headers(self):
        data = [
            (u'Chapter 1 Title\n===============\n\nSection 1.1 Title\n-----------------\n\nSubsection 1.1.1 Title\n~~~~~~~~~~~~~~~~~~~~~~\n\nSection 1.2 Title\n-----------------\n\nChapter 2 Title\n===============\n', '<page><body><h outline-level="2">Chapter 1 Title</h><h outline-level="3">Section 1.1 Title</h><h outline-level="4">Subsection 1.1.1 Title</h><h outline-level="3">Section 1.2 Title</h><h outline-level="2">Chapter 2 Title</h></body></page>'),
            (u'================\n Document Title\n================\n\n----------\n Subtitle\n----------\n\nSection Title\n=============', '<page><body><h outline-level="1">Document Title</h><h outline-level="2">Subtitle</h><h outline-level="2">Section Title</h></body></page>')
            ]
        for i in data:
            yield (self.do, ) + i

    def test_footnote(self):
        data = [
            (u'Abra [1]_\n\n.. [1] arba', '<page><body><p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p></body></page>'),
            (u'Abra [#]_\n\n.. [#] arba', '<page><body><p>Abra <note note-class="footnote"><note-body>arba</note-body></note></p></body></page>'),
            ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'Abra test_ arba\n\n.. _test: http://python.org', '<page><body><p>Abra <a xlink:href="http://python.org">test</a> arba</p></body></page>'),
            (u'Abra test__ arba\n\n.. __: http://python.org', '<page><body><p>Abra <a xlink:href="http://python.org">test</a> arba</p></body></page>')
            ]
        for i in data:
            yield (self.do, ) + i

    def test_directive(self):
        data = [
            (u'.. macro:: <<TableOfContents()>>', '<page><body><table-of-content /></body></page>'),
            (u'.. macro:: <<Macro()>>', '<page><body><part content-type="x-moin/macro;name=Macro"><arguments><argument></argument></arguments>&lt;&lt;Macro()&gt;&gt;</part></body></page>'),
            (u'.. macro:: Macro(arg)', '<page><body><part content-type="x-moin/macro;name=Macro"><arguments><argument>arg</argument></arguments>&lt;&lt;Macro(arg)&gt;&gt;</part></body></page>'),
            (u'test |a| test\n\n.. |a| macro:: <<Macro()>>', '<page><body><p>test <part content-type="x-moin/macro;name=Macro"><arguments><argument></argument></arguments>&lt;&lt;Macro()&gt;&gt;</part> test</p></body></page>'),
            (u'.. contents::\n  :depth: 1\n', '<page><body><table-of-content outline-level="1" /></body></page>'),
            (u'.. parser:: python test=test\n  import test\n  test.s = 11', '<page><body><part content-type="x-moin/format;name=python"><arguments><argument name="test">test</argument></arguments>import test\ntest.s = 11</part></body></page>'),
            (u'.. include:: RecentChanges', '<page><body><part content-type="x-moin/macro;name=Include"><arguments><argument>RecentChanges</argument></arguments>&lt;&lt;Include(RecentChanges)&gt;&gt;</part></body></page>'),
            ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n", '<page><body><table><table-body><table-row><table-cell><p>A</p></table-cell><table-cell><p>B</p></table-cell><table-cell number-rows-spanned="2"><p>D</p></table-cell></table-row><table-row><table-cell number-cols-spanned="2"><p>C</p></table-cell></table-row></table-body></table></body></page>'),
            (u"+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n", '<page><body><table><table-body><table-row><table-cell><p><strong>A</strong></p></table-cell><table-cell><p><strong>B</strong></p></table-cell><table-cell><p><strong>C</strong></p></table-cell></table-row><table-row><table-cell><p>1</p></table-cell><table-cell><p>2</p></table-cell><table-cell><p>3</p></table-cell></table-row></table-body></table></body></page>'),
            ("""+--------------------+-------------------------------------+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""", '<page><body><table><table-body><table-row><table-cell number-rows-spanned="2"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-cols-spanned="2"><p>test</p></table-cell></table-row><table-row><table-cell number-cols-spanned="2"><p>test</p></table-cell></table-row></table-body></table></body></page>'),
            ("""
+--------------------+-------------------------------------+
| AAAAAAAAAAAAAAAAAA | BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB |
+====================+=====================================+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""", '<page><body><table><table-header><table-row><table-cell><p>AAAAAAAAAAAAAAAAAA</p></table-cell><table-cell><p>BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB</p></table-cell></table-row></table-header><table-body><table-row><table-cell number-rows-spanned=\"2\"><p>cell spanning 2 rows</p></table-cell><table-cell><p>cell in the 2nd column</p></table-cell></table-row><table-row><table-cell><p>cell in the 2nd column of the 2nd row</p></table-cell></table-row><table-row><table-cell number-cols-spanned=\"2\"><p>test</p></table-cell></table-row><table-row><table-cell number-cols-spanned=\"2\"><p>test</p></table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_docutils_feature(self):
        data = [
            (u':Author: Test\n:Version:  $Revision: 1.17 $\n:Copyright: c\n:Test: t', '<page><body><table><table-body><table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Test</table-cell></table-row><table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1.17</table-cell></table-row><table-row><table-cell><strong>Copyright:</strong></table-cell><table-cell>c</table-cell></table-row><table-row><table-cell><strong>Test:</strong></table-cell><table-cell><p>t</p></table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input, 'text/x-rst;charset=utf-8', **args)
        assert self.serialize(out) == output


coverage_modules = ['MoinMoin.converter.rst_in']
