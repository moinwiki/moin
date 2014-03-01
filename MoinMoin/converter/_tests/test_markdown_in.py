# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter.markdown_in
"""


import re

from MoinMoin.util.tree import moin_page, xlink

from ..markdown_in import Converter


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
                '<p>Text</p>'),
            (u'Text\nTest',
                '<p>Text\nTest</p>'),
            (u'Text\n\nTest',
                '<p>Text</p>\n<p>Test</p>'),
            (u'<http://moinmo.in/>',
                '<p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p>'),
            (u'[yo](javascript:alert("xss"))',
                '<p>javascript:alert("xss")</p>'),
            (u'[MoinMoin](http://moinmo.in/)',
                '<p><a xlink:href="http://moinmo.in/">MoinMoin</a></p>'),
            (u'----',
                '<separator />'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_emphasis(self):
        data = [
            (u'*Emphasis*',
                '<p><emphasis>Emphasis</emphasis></p>'),
            (u'_Emphasis_',
                '<p><emphasis>Emphasis</emphasis></p>'),
            (u'**Strong**',
                '<p><strong>Strong</strong></p>'),
            (u'_**Both**_',
                '<p><emphasis><strong>Both</strong></emphasis></p>'),
            (u'**_Both_**',
                '<p><strong><emphasis>Both</emphasis></strong></p>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_escape(self):
        data = [
            (u'http://moinmo.in/',
                '<p>http://moinmo.in/</p>'),
            (u'\[escape](yo)',
                '<p>[escape](yo)</p>'),
            (u'\*yo\*',
                '<p>*yo*</p>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_heading(self):
        data = [
            (u'# Heading 1',
                '<h outline-level="1">Heading 1</h>'),
            (u'## Heading 2',
                '<h outline-level="2">Heading 2</h>'),
            (u'### Heading 3',
                '<h outline-level="3">Heading 3</h>'),
            (u'#### Heading 4',
                '<h outline-level="4">Heading 4</h>'),
            (u'##### Heading 5',
                '<h outline-level="5">Heading 5</h>'),
            (u'###### Heading 6',
                '<h outline-level="6">Heading 6</h>'),
            (u'# Heading 1 #',
                '<h outline-level="1">Heading 1</h>'),
            (u'## Heading 2 ##',
                '<h outline-level="2">Heading 2</h>'),
            (u'### Heading 3 ###',
                '<h outline-level="3">Heading 3</h>'),
            (u'#### Heading 4 ####',
                '<h outline-level="4">Heading 4</h>'),
            (u'##### Heading 5 #####',
                '<h outline-level="5">Heading 5</h>'),
            (u'###### Heading 6 ######',
                '<h outline-level="6">Heading 6</h>'),
            (u'Heading 1\n=========\nHeading 2\n---------\n',
                '<h outline-level="1">Heading 1</h>\n<h outline-level="2">Heading 2</h>'),
            (u'Heading 1\n---------\n',
                '<h outline-level="2">Heading 1</h>'),
            (u'Heading\n=======\n\nxxxx',
                '<h outline-level="1">Heading</h>\n<p>xxxx</p>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u'* Item',
                '<list item-label-generate="unordered">\n<list-item><list-item-body>Item</list-item-body></list-item>\n</list>'),
            (u'* Item\nItem',
                '<list item-label-generate="unordered">\n<list-item><list-item-body>Item\nItem</list-item-body></list-item>\n</list>'),
            (u'* Item 1\n* Item 2',
                '<list item-label-generate="unordered">\n<list-item><list-item-body>Item 1</list-item-body></list-item>\n<list-item><list-item-body>Item 2</list-item-body></list-item>\n</list>'),
            (u'* Item 1\n    * Item 1.2\n* Item 2',
                '<list item-label-generate="unordered">\n<list-item><list-item-body>Item 1<list item-label-generate="unordered">\n<list-item><list-item-body>Item 1.2</list-item-body></list-item>\n</list>\n</list-item-body></list-item>\n<list-item><list-item-body>Item 2</list-item-body></list-item>\n</list>'),
            (u'* List 1\n\nyo\n\n\n* List 2',
                '<list item-label-generate="unordered">\n<list-item><list-item-body>List 1</list-item-body></list-item>\n</list>\n<p>yo</p>\n<list item-label-generate="unordered">\n<list-item><list-item-body>List 2</list-item-body></list-item>\n</list>'),
            (u'8. Item',
                '<list item-label-generate="ordered">\n<list-item><list-item-body>Item</list-item-body></list-item>\n</list>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}):
        out = self.conv(input, 'text/x-markdown;charset=utf-8', **args)
        got_output = self.serialize(out)
        desired_output = "<page><body>\n%s\n</body></page>" % output
        print '------------------------------------'
        print "WANTED:"
        print desired_output
        print "GOT:"
        print got_output
        assert got_output == desired_output
