# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.mediawiki_in
"""


import pytest
import re

from MoinMoin.converter.mediawiki_in import *


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
            (u"''italic''", u'<page><body><p><emphasis>italic</emphasis></p></body></page>'),
            (u"Text\nTest", u'<page><body><p>Text\nTest</p></body></page>'),
            (u'Text\n\nTest', u'<page><body><p>Text</p><p>Test</p></body></page>'),
            (u"'''bold'''", u'<page><body><p><strong>bold</strong></p></body></page>'),
            (u"'''''bold and italic'''''", u'<page><body><p><strong><emphasis>bold and italic</emphasis></strong></p></body></page>'),
            (u"<nowiki>no ''markup''</nowiki>\n\n<code>no ''markup''</code>\n\n<tt>no ''markup''</tt>", "<page><body><p><code>no ''markup''</code></p><p><code>no ''markup''</code></p><p><code>no ''markup''</code></p></body></page>"),
            (u"<pre>no ''markup'' block</pre>", u"<page><body><p><blockcode>no ''markup'' block</blockcode></p></body></page>"),
            (u'<u>underscore</u>', u'<page><body><p><span text-decoration="underline">underscore</span></p></body></page>'),
            (u'<del>Strikethrough</del>', u'<page><body><p><span text-decoration="line-through">Strikethrough</span></p></body></page>'),
            (u"test <sup>super</sup> or <sub>sub</sub>", u'<page><body><p>test <span baseline-shift="super">super</span> or <span baseline-shift="sub">sub</span></p></body></page>'),
            (u"text <blockquote> quote quote quote quote quote quote </blockquote> text", u"<page><body><p>text <blockquote> quote quote quote quote quote quote </blockquote> text</p></body></page>"),
            (u"aaa<br />bbb", u"<page><body><p>aaa<line-break />bbb</p></body></page>"),
            (u"aaa <ref> sdf </ref> test\n\n asd", '<page><body><p>aaa <note note-class="footnote"><note-body> sdf </note-body></note> test</p><p> asd</p></body></page>'),
            (u"""=level 1=
== level 2 ==
===level 3===
====level 4====
=====level 5=====
======level 6======
""", u'<page><body><h outline-level="1">level 1</h><h outline-level="2">level 2</h><h outline-level="3">level 3</h><h outline-level="4">level 4</h><h outline-level="5">level 5</h><h outline-level="6">level 6</h></body></page>'),
            (u"[javascript:alert('xss')]", "<page><body><p>[javascript:alert('xss')]</p></body></page>"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u"""* one
* two
* three
** three point one
** three point two
""", u'<page><body><list item-label-generate="unordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two</p></list-item-body></list-item><list-item><list-item-body><p>three</p><list item-label-generate="unordered"><list-item><list-item-body><p>three point one</p></list-item-body></list-item><list-item><list-item-body><p>three point two</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>'),
            (u"""# one
# two<br />spanning more lines<br />doesn't break numbering
# three
## three point one
## three point two
# 4
no point
""", u'''<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two<line-break />spanning more lines<line-break />doesn't break numbering</p></list-item-body></list-item><list-item><list-item-body><p>three</p><list item-label-generate="ordered"><list-item><list-item-body><p>three point one</p></list-item-body></list-item><list-item><list-item-body><p>three point two</p></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>4</p></list-item-body></list-item></list><p>no point</p></body></page>'''),
            (""";item 1:definition 1
;item 2:definition 2
""", u'''\
<page><body>\
<list>\
<list-item>\
<list-item-label>item 1</list-item-label>\
<list-item-body><p>definition 1</p></list-item-body>\
</list-item>\
<list-item>\
<list-item-label>item 2</list-item-label>\
<list-item-body><p>definition 2</p></list-item-body>\
</list-item>\
</list>\
</body></page>\
'''),
            # TODO add a test for a definition list with term and definition on separate lines like:
            # ; term
            # : definition
            (u";aaa : bbb", u"<page><body><list><list-item><list-item-label>aaa </list-item-label><list-item-body><p> bbb</p></list-item-body></list-item></list></body></page>"),
            (u""": Single indent
:: Double indent
::::: Multiple indent
""", u'<page><body><list item-label-generate="None"><list-item><list-item-body><p>Single indent</p><list item-label-generate="None"><list-item><list-item-body><p>Double indent</p><list item-label-generate="None"><list-item><list-item-body><p>Multiple indent</p></list-item-body></list-item></list></list-item-body></list-item></list></list-item-body></list-item></list></body></page>'),
            ("""# one
# two
#* two point one
#* two point two
# three
#; three item one:three def one
""", u'<page><body><list item-label-generate="ordered"><list-item><list-item-body><p>one</p></list-item-body></list-item><list-item><list-item-body><p>two</p><list item-label-generate="unordered"><list-item><list-item-body><p>two point one</p></list-item-body></list-item><list-item><list-item-body><p>two point two</p></list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body><p>three</p><list><list-item><list-item-label>three item one</list-item-label><list-item-body><p>three def one</p></list-item-body></list-item></list></list-item-body></list-item></list></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"""{|
|Orange
|Apple
|-
|Bread
|Pie
|-
|Butter
|Ice cream
|}
""", u"<page><body><table><table-body><table-row><table-cell>Orange</table-cell><table-cell>Apple</table-cell></table-row><table-row><table-cell>Bread</table-cell><table-cell>Pie</table-cell></table-row><table-row><table-cell>Butter</table-cell><table-cell>Ice cream</table-cell></table-row></table-body></table></body></page>"),
            (u"""{|style="border-width: 1px;"
|style="border-style: solid; border-width: 1px" colspan="2"| Orange
Apple
|-
|rowspan='2'| Bread
|Pie
|-
|test
|}
""", u'<page><body><table style="border-width: 1px;"><table-body><table-row><table-cell number-columns-spanned="2" style="border-style: solid; border-width: 1px">Orange\nApple</table-cell></table-row><table-row><table-cell number-rows-spanned="2">Bread</table-cell><table-cell>Pie</table-cell></table-row><table-row><table-cell>test</table-cell></table-row></table-body></table></body></page>'),
("""{|
|class="test"|text||style="border:1px"|test
|}
""", u'<page><body><table><table-body><table-row><table-cell class="test">text</table-cell><table-cell style="border:1px">test</table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_links(self):
        data = [
            (u"[[SomeLink]]", u'<page><body><p><a xlink:href="wiki.local:SomeLink">SomeLink</a></p></body></page>'),
            (u"[http://external.link]", u'<page><body><p><a xlink:href="http://external.link"></a></p></body></page>'),
            (u"[http://external.link alt text]", u'<page><body><p><a xlink:href="http://external.link">alt text</a></p></body></page>'),
            (u"[[SomeLink|Some text]]", u'<page><body><p><a xlink:href="wiki.local:SomeLink">Some text</a></p></body></page>'),
            (u"[[File:Test.jpg|test]]", u'<page><body><p><object alt="test" xlink:href="wiki.local:Test.jpg?do=get">test</object></p></body></page>')
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input, 'text/x-mediawiki;charset=utf-8', **args)
        print self.serialize(out)
        assert self.serialize(out) == output

coverage_modules = ['MoinMoin.converter.mediawiki_in']
