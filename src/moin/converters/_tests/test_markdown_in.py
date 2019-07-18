# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.markdown_in
"""

import pytest

from . import serialize, XMLNS_RE

from moin.utils.tree import moin_page, xlink, xml, xinclude, html

from ..markdown_in import Converter


class TestConverter(object):
    namespaces = {
        moin_page: '',
        xlink: 'xlink',
        xml: 'xml',
        xinclude: 'xinclude',
        html: 'html',
    }

    output_re = XMLNS_RE

    def setup_class(self):
        self.conv = Converter()

    data = [
        ('Text',
         '<p>Text</p>'),
        ('Text\nTest',
         '<p>Text\nTest</p>'),
        ('Text\n\nTest',
         '<p>Text</p><p>Test</p>'),
        ('<http://moinmo.in/>',
         '<p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p>'),
        ('[yo](javascript:alert("xss"))',
         '<p>javascript:alert()</p>'),
        ('[MoinMoin](http://moinmo.in/)',
         '<p><a xlink:href="http://moinmo.in/">MoinMoin</a></p>'),
        ('----',
         '<separator class="moin-hr3" />'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        ('*Emphasis*',
         '<p><emphasis>Emphasis</emphasis></p>'),
        ('_Emphasis_',
         '<p><emphasis>Emphasis</emphasis></p>'),
        ('**Strong**',
         '<p><strong>Strong</strong></p>'),
        ('_**Both**_',
         '<p><emphasis><strong>Both</strong></emphasis></p>'),
        ('**_Both_**',
         '<p><strong><emphasis>Both</emphasis></strong></p>'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_emphasis(self, input, output):
        self.do(input, output)

    data = [
        ('http://moinmo.in/',
         '<p>http://moinmo.in/</p>'),
        ('\\[escape](yo)',
         '<p>[escape](yo)</p>'),
        ('\\*yo\\*',
         '<p>*yo*</p>'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_escape(self, input, output):
        self.do(input, output)

    data = [
        ('# Heading 1',
         '<h outline-level="1" xml:id="heading-1">Heading 1</h>'),
        ('## Heading 2',
         '<h outline-level="2" xml:id="heading-2">Heading 2</h>'),
        ('### Heading 3',
         '<h outline-level="3" xml:id="heading-3">Heading 3</h>'),
        ('#### Heading 4',
         '<h outline-level="4" xml:id="heading-4">Heading 4</h>'),
        ('##### Heading 5',
         '<h outline-level="5" xml:id="heading-5">Heading 5</h>'),
        ('###### Heading 6',
         '<h outline-level="6" xml:id="heading-6">Heading 6</h>'),
        ('# Heading 1 #',
         '<h outline-level="1" xml:id="heading-1">Heading 1</h>'),
        ('## Heading 2 ##',
         '<h outline-level="2" xml:id="heading-2">Heading 2</h>'),
        ('### Heading 3 ###',
         '<h outline-level="3" xml:id="heading-3">Heading 3</h>'),
        ('#### Heading 4 ####',
         '<h outline-level="4" xml:id="heading-4">Heading 4</h>'),
        ('##### Heading 5 #####',
         '<h outline-level="5" xml:id="heading-5">Heading 5</h>'),
        ('###### Heading 6 ######',
         '<h outline-level="6" xml:id="heading-6">Heading 6</h>'),
        ('Heading 1\n=========\nHeading 2\n---------\n',
         '<h outline-level="1" xml:id="heading-1">Heading 1</h><h outline-level="2" xml:id="heading-2">Heading 2</h>'),
        ('Heading 2\n---------\n',
         '<h outline-level="2" xml:id="heading-2">Heading 2</h>'),
        ('Heading\n=======\n\nxxxx',
         '<h outline-level="1" xml:id="heading">Heading</h><p>xxxx</p>'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_heading(self, input, output):
        self.do(input, output)

    data = [
        ('* Item',
         '<list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list>'),
        ('* Item\nItem',
         '<list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list>'),
        ('* Item 1\n* Item 2',
         '<list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>'),
        ('* Item 1\n    * Item 1.2\n* Item 2',
         '<list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>'),
        ('* List 1\n\nyo\n\n\n* List 2',
         '<list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><p>yo</p><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list>'),
        ('8. Item',
         '<list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list>'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        ('![Alt text](png "Optional title")',
         '<p><xinclude:include html:alt="Alt text" html:title="Optional title" xinclude:href="wiki.local:png" /></p>'),
        ('![](png "Optional title")',
         '<p><xinclude:include html:title="Optional title" xinclude:href="wiki.local:png" /></p>'),
        ('![remote image](http://static.moinmo.in/logos/moinmoin.png)',
         '<p><object html:alt="remote image" xlink:href="http://static.moinmo.in/logos/moinmoin.png" /></p>'),
        ('![Alt text](http://test.moinmo.in/png)',
         '<p><object html:alt="Alt text" xlink:href="http://test.moinmo.in/png" /></p>'),
        ('![transclude local wiki item](someitem)',
         '<p><xinclude:include html:alt="transclude local wiki item" xinclude:href="wiki.local:someitem" /></p>'),
    ]

    @pytest.mark.parametrize('input,output', data)
    def test_image(self, input, output):
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub('', result)

    def do(self, input, output, args={}):
        out = self.conv(input, 'text/x-markdown;charset=utf-8', **args)
        got_output = self.serialize_strip(out)
        desired_output = "<page><body>%s</body></page>" % output
        print('------------------------------------')
        print("WANTED:")
        print(desired_output)
        print("GOT:")
        print(got_output)
        assert got_output == desired_output
