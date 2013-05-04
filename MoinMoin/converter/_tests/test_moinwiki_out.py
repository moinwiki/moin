# -*- coding: utf-8 -*-
# Copyright: 2010 MoinMoin:DmitryAndreev
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.moinwiki_out
"""


import re

from MoinMoin.converter.moinwiki_out import *


class Base(object):
    input_namespaces = ns_all = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}"'.format(moin_page.namespace, moin_page.namespace, xlink.namespace)
    output_namespaces = {
        moin_page.namespace: 'page'
    }

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i.encode("utf-8"))

    def handle_output(self, elem, **options):
        return elem

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        assert self.handle_output(out) == output


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            (u'<page:p>Текст</page:p>', u'Текст\n'),
            (u'<page:p>Text</page:p>', u'Text\n'),
            (u"<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", 'Text\n\nText\n'),
            (u"<page:separator />", '----\n'),
            (u"<page:strong>strong</page:strong>", "'''strong'''"),
            (u"<page:emphasis>emphasis</page:emphasis>", "''emphasis''"),
            (u"<page:blockcode>blockcode</page:blockcode>", "{{{\nblockcode\n}}}\n"),
            (u"<page:code>monospace</page:code>", '`monospace`'),
            (u'<page:span page:text-decoration="line-through">stroke</page:span>', '--(stroke)--'),
            (u'<page:span page:text-decoration="underline">underline</page:span>', '__underline__'),
            (u'<page:span page:font-size="120%">larger</page:span>', '~+larger+~'),
            (u'<page:span page:font-size="85%">smaller</page:span>', '~-smaller-~'),
            (u'<page:tag><page:span page:baseline-shift="super">super</page:span>script</page:tag>', '^super^script'),
            (u'<page:tag><page:span page:baseline-shift="sub">sub</page:span>script</page:tag>', ',,sub,,script'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'<page:a xlink:href="wiki.local:SomePage#subsection">subsection of Some Page</page:a>', '[[SomePage#subsection|subsection of Some Page]]'),
            (u'<page:a xlink:target="_blank" xlink:href="wiki.local:SomePage">{{attachment:samplegraphic.png}}</page:a>', '[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]'),
            (u'<page:a xlink:href="wiki.local:SomePage?target=_blank">{{attachment:samplegraphic.png}}</page:a>', '[[SomePage|{{attachment:samplegraphic.png}}|&target=_blank]]'),
            (u'<page:a xlink:href="../SisterPage">link text</page:a>', '[[../SisterPage|link text]]'),
            (u'<page:a xlink:target="_blank" xlink:class="aaa" xlink:href="http://static.moinmo.in/logos/moinmoin.png">{{attachment:samplegraphic.png}}</page:a>', '[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank,class=aaa]]'),
            (u'<page:a xlink:class="green dotted" xlink:accesskey="1" xlink:href="http://moinmo.in/">MoinMoin Wiki</page:a>', '[[http://moinmo.in/|MoinMoin Wiki|accesskey=1,class=green dotted]]'),
            (u'<page:a xlink:href="MoinMoin:MoinMoinWiki?action=diff&amp;rev1=1&amp;rev2=2">MoinMoin Wiki</page:a>', '[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]'),
            (u'<page:a xlink:href="attachment:HelpOnImages/pineapple.jpg?do=get">a pineapple</page:a>', '[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]'),
            (u'<page:a xlink:href="attachment:filename.txt">attachment:filename.txt</page:a>', '[[attachment:filename.txt]]')
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            (u"<page:object xlink:href=\"drawing:anywikitest.adraw\">{{drawing:anywikitest.adraw</page:object>", '{{drawing:anywikitest.adraw}}'),
            (u"<page:object xlink:href=\"http://static.moinmo.in/logos/moinmoin.png\" />", '{{http://static.moinmo.in/logos/moinmoin.png}}'),
            (u'<page:object page:alt="alt text" xlink:href="http://static.moinmo.in/logos/moinmoin.png">alt text</page:object>', '{{http://static.moinmo.in/logos/moinmoin.png|alt text}}'),
            (u'<page:object xlink:href="attachment:image.png" />', '{{attachment:image.png}}'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png">alt text</page:object>', '{{attachment:image.png|alt text}}'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png?width=100&amp;height=150&amp;align=left" />', '{{attachment:image.png|alt text|width=100 height=150 align=left}}'),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " * A\n"),
            (u"<page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " 1. A\n"),
            (u"<page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " I. A\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>", " * A\n * B\n   1. C\n   1. D\n      I. E\n      I. F\n"),
            (u"<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>", " A::\n :: B\n :: C\n :: D\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned=\"2\">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">C</page:table-cell></page:table-row></page:table-body></page:table>", "||A||B||<|2>D||\n||||C||\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>", u"||'''A'''||'''B'''||'''C'''||\n||1||2||3||\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned=\"2\">cell spanning 2 rows</page:table-cell><page:table-cell>cell in the 2nd column</page:table-cell></page:table-row><page:table-row><page:table-cell>cell in the 2nd column of the 2nd row</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row></page:table-body></page:table>", "||<|2>cell spanning 2 rows||cell in the 2nd column||\n||cell in the 2nd column of the 2nd row||\n||||test||\n||||test||\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macros(self):
        data = [
            (u"<page:note page:note-class=\"footnote\"><page:note-body>test</page:note-body></page:note>", "<<FootNote(test)>>"),
            (u"<page:tag><page:table-of-content page:outline-level=\"2\" /></page:tag>", "<<TableOfContents(2)>>\n"),
            (u"<page:part page:alt=\"&lt;&lt;Anchor(anchorname)&gt;&gt;\" page:content-type=\"x-moin/macro;name=Anchor\"><page:arguments><page:argument>anchorname</page:argument></page:arguments></page:part>", "<<Anchor(anchorname)>>\n"),
            (u"<page:part page:alt=\"&lt;&lt;MonthCalendar(,,12)&gt;&gt;\" page:content-type=\"x-moin/macro;name=MonthCalendar\"><page:arguments><page:argument /><page:argument /><page:argument>12</page:argument></page:arguments></page:part>", "<<MonthCalendar(,,12)>>\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_parser(self):
        data = [
            (u"<page:page><page:body><page:page><page:body page:class=\"comment dotted\"><page:p>This is a wiki parser.</page:p><page:p>Its visibility gets toggled the same way.</page:p></page:body></page:page></page:body></page:page>", "{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}\n"),
            (u"<page:page><page:body><page:page><page:body page:class=\"red solid\"><page:p>This is wiki markup in a <page:strong>div</page:strong> with <page:span page:text-decoration=\"underline\">css</page:span> <page:code>class=\"red solid\"</page:code>.</page:p></page:body></page:page></page:body></page:page>", "{{{#!wiki red/solid\nThis is wiki markup in a \'\'\'div\'\'\' with __css__ `class=\"red solid\"`.\n}}}\n"),
            (u"<page:page><page:body><page:part page:content-type=\"x-moin/format;name=creole\"><page:arguments><page:argument page:name=\"style\">st: er</page:argument><page:argument page:name=\"class\">par: arg para: arga</page:argument></page:arguments><page:body>... **bold** ...</page:body></page:part></page:body></page:page>", "{{{#!creole(style=\"st: er\" class=\"par: arg para: arga\")\n... **bold** ...\n}}}\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_p(self):
        data = [
            (u"<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>", "A\n\nB\n\nC\n\nD\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "||Z||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "||Z||\n||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p>A<page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " * A<<BR>>A\n * A<<BR>>A<<BR>>A\n * A\n")
        ]
        for i in data:
            yield (self.do, ) + i

    def test_separator(self):
        data = [
            (u"<page:page><page:body><page:p>A</page:p><page:separator /></page:body></page:page>", "A\n----\n"),
            (u"<page:page><page:body><page:p>A</page:p><page:separator page:class=\"moin-hr1\"/></page:body></page:page>", "A\n----\n"),
            (u"<page:page><page:body><page:p>A</page:p><page:separator page:class=\"moin-hr3\"/></page:body></page:page>", "A\n------\n"),
            (u"<page:page><page:body><page:p>A</page:p><page:separator page:class=\"moin-hr6\"/></page:body></page:page>", "A\n---------\n"),
        ]
        for i in data:
            yield (self.do, ) + i

coverage_modules = ['MoinMoin.converter.moinwiki_out']
