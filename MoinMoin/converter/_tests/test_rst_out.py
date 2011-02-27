"""
MoinMoin - Tests for MoinMoin.converter.rst_out

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import py.test
import re

from MoinMoin.converter.rst_out import *


class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        xlink.namespace)
    output_namespaces = {
        moin_page.namespace: 'page'
    }

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

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
            (u'<page:p>Text</page:p>', 'Text\n'),
            (u"<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", 'Text\n\nText\n'),
            (u"<page:separator />", '\n\n----\n\n'),
            (u"<page:strong>strong</page:strong>", "**strong**"),
            (u"<page:emphasis>emphasis</page:emphasis>", "*emphasis*"),
            (u"<page:blockcode>blockcode</page:blockcode>", "::\n\n  blockcode\n\n"),
            (u"<page:code>monospace</page:code>", '``monospace``'),
            (u"""<page:page><page:body><page:h page:outline-level="1">h1</page:h><page:h page:outline-level="2">h2</page:h><page:h page:outline-level="3">h3</page:h><page:h page:outline-level="4">h4</page:h><page:h page:outline-level="5">h5</page:h><page:h page:outline-level="6">h6</page:h></page:body></page:page>""", u"""\n\n--\nh1\n--\n\n\n\n``\nh2\n``\n\n\n\n::\nh3\n::\n\n\n\n\'\'\nh4\n\'\'\n\n\n\n""\nh5\n""\n\n\n\n~~\nh6\n~~\n\n"""),
            (u'<page:page><page:body><page:p>H<page:span page:baseline-shift="sub">2</page:span>O</page:p><page:p>E = mc<page:span page:baseline-shift="super">2</page:span></page:p></page:body></page:page>', u'H\\ :sub:`2`\\ O\n\nE = mc\\ :sup:`2`\\ \n'),
            (u'<page:page><page:body><page:p>H<page:span>2</page:span>O</page:p></page:body></page:page>', 'H2O\n')
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", "* A\n\n"),
            (u"<page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", "1. A\n\n"),
            (u"<page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>", "I. A\n\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>", "* A\n\n* B\n\n  1. C\n\n  #. D\n\n     I. E\n\n     #. F\n\n"),
            (u"<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>", "A\n  B\n\n  C\n\n  D\n\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned=\"2\">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned=\"2\">C</page:table-cell></page:table-row></page:table-body></page:table>", "+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>", u"+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n"),
             (u'<page:page><page:body><page:table><page:table-header><page:table-row><page:table-cell><page:p>AAAAAAAAAAAAAAAAAA</page:p></page:table-cell><page:table-cell><page:p>BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB</page:p></page:table-cell></page:table-row></page:table-header><page:table-body><page:table-row><page:table-cell page:number-rows-spanned=\"2\"><page:p>cell spanning 2 rows</page:p></page:table-cell><page:table-cell><page:p>cell in the 2nd column</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>cell in the 2nd column of the 2nd row</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned=\"2\"><page:p>test</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned=\"2\"><page:p>test</page:p></page:table-cell></page:table-row></page:table-body></page:table></page:body></page:page>', """+--------------------+-------------------------------------+
|AAAAAAAAAAAAAAAAAA  |BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB  |
+====================+=====================================+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

"""),
            (u"<page:table><page:table-body><page:table-row><page:table-cell page:number-cols-spanned=\"2\"><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned=\"2\"><page:p>1</page:p></page:table-cell></page:table-row></page:table-body></page:table>", u"+------+-----+\n|**A** |**C**|\n+------+-----+\n|1     |     |\n+------+-----+\n\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_p(self):
        data = [
            (u"<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>", "A\n\nB\n\nC\n\nD\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+-+\n|Z|A|\n| | |\n| |B|\n| | |\n| |C|\n| | |\n| |D|\n+-+-+\n\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+\n|Z|\n+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n"),
            (u"<page:page><page:body>A<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p>A<page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>A</page:body></page:page>", "A\n\n* A\n\n  A\n\n* A\n\n  A\n\n  A\n\n* A\n\nA")
        ]
        for i in data:
            yield (self.do, ) + i

    def test_docutils_features(self):
        data = [
            (u'<page><body><table><table-body><table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Test</table-cell></table-row><table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1.17</table-cell></table-row><table-row><table-cell><strong>Copyright:</strong></table-cell><table-cell>c</table-cell></table-row><table-row><table-cell><strong>Test:</strong></table-cell><table-cell><p>t</p></table-cell></table-row></table-body></table></body></page>', """+--------------+----+
|**Author:**   |Test|
+--------------+----+
|**Version:**  |1.17|
+--------------+----+
|**Copyright:**|c   |
+--------------+----+
|**Test:**     |t   |
+--------------+----+

"""),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_note(self):
        data = [
            (u'<page:page><page:body><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p></page:body></page:page>', u'Abra  [#]_ \n\n\n.. [#] arba\n\n'),
            (u'<page:page><page:body><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p><page:p>Abra <page:note page:note-class="footnote">arba</page:note><page:note page:note-class="footnote">arba</page:note></page:p></page:body></page:page>', u'Abra  [#]_ \n\nAbra  [#]_ \n\nAbra  [#]_  [#]_ \n\n\n.. [#] arba\n\n.. [#] arba\n\n.. [#] arba\n\n.. [#] arba\n\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba</page:p></page:body></page:page>', u'Abra `test`_ arba\n\n\n.. _test: http://python.org\n\n'),
            (u'<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba <page:a xlink:href="http://python.ru">test</page:a></page:p></page:body></page:page>', u'Abra `test`_ arba `test`__\n\n\n.. __: http://python.ru\n\n.. _test: http://python.org\n\n'),
            (u'<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba <page:a xlink:href="http://python.ru">test</page:a> rbaa <page:a xlink:href="http://python.su">test</page:a></page:p></page:body></page:page>', u'Abra `test`_ arba `test`__ rbaa `test~`_\n\n\n.. __: http://python.ru\n\n.. _test: http://python.org\n\n.. _test~: http://python.su\n\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_mixed(self):
        data = [
            (u"<page:page><page:body><page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Author:</page:strong></page:table-cell><page:table-cell>Test</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Version:</page:strong></page:table-cell><page:table-cell>1.17</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Copyright:</page:strong></page:table-cell><page:table-cell>c</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Test:</page:strong></page:table-cell><page:table-cell><page:p>t</page:p></page:table-cell></page:table-row></page:table-body></page:table></page:list-item-body></page:list-item></page:list></page:body></page:page>", """* A

  +--------------+----+
  |**Author:**   |Test|
  +--------------+----+
  |**Version:**  |1.17|
  +--------------+----+
  |**Copyright:**|c   |
  +--------------+----+
  |**Test:**     |t   |
  +--------------+----+

"""),
            (u"<page:page><page:body><page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:blockcode> test </page:blockcode></page:list-item-body></page:list-item></page:list></page:body></page:page>", u"* A::\n\n     test \n\n\n"),
            (u'<page:page><page:body><page:table><page:table-body><page:table-row><page:table-cell><page:p><page:strong>A</page:strong></page:p><page:line_break /><page:p><page:strong>A</page:strong></page:p></page:table-cell><page:table-cell><page:strong>B</page:strong><page:line_break /><page:strong>B</page:strong></page:table-cell></page:table-row></page:table-body></page:table></page:body></page:page>', '+-----+-----+\n|**A**|**B**|\n|     |     |\n|**A**|**B**|\n+-----+-----+\n\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            (u"<page:object xlink:href=\"drawing:anywikitest.adraw\">{{drawing:anywikitest.adraw</page:object>", '\n\n..  image:: drawing:anywikitest.adraw\n\n'),
            (u"<page:object xlink:href=\"http://static.moinmo.in/logos/moinmoin.png\" />", '\n\n..  image:: http://static.moinmo.in/logos/moinmoin.png\n\n'),
            (u'<page:object page:alt="alt text" xlink:href="http://static.moinmo.in/logos/moinmoin.png">alt text</page:object>', u'|alt text|\n\n.. |alt text| image:: http://static.moinmo.in/logos/moinmoin.png\n\n'),
            (u'<page:object xlink:href="attachment:image.png" />', '\n\n..  image:: attachment:image.png\n\n'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png">alt text</page:object>', '|alt text|\n\n.. |alt text| image:: attachment:image.png\n\n'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png?width=100&amp;height=150&amp;align=left" />', '|alt text|\n\n.. |alt text| image:: attachment:image.png\n  :width: 100\n  :height: 150\n  :align: left\n\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macros(self):
        data = [
            (u"<page:tag><page:table-of-content page:outline-level=\"2\" /></page:tag>", "\n\n.. contents::\n   :depth: 2\n\n"),
            (u"<page:part page:alt=\"&lt;&lt;Anchor(anchorname)&gt;&gt;\" page:content-type=\"x-moin/macro;name=Anchor\"><page:arguments><page:argument>anchorname</page:argument></page:arguments></page:part>", " |<<Anchor(anchorname)>>| \n\n.. |<<Anchor(anchorname)>>| macro:: <<Anchor(anchorname)>>\n\n"),
            (u"<page:part page:alt=\"&lt;&lt;MonthCalendar(,,12)&gt;&gt;\" page:content-type=\"x-moin/macro;name=MonthCalendar\"><page:arguments><page:argument /><page:argument /><page:argument>12</page:argument></page:arguments></page:part>", u' |<<MonthCalendar(,,12)>>| \n\n.. |<<MonthCalendar(,,12)>>| macro:: <<MonthCalendar(,,12)>>\n\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_parser(self):
        data = [
            (u"<page:page><page:body><page:part page:content-type=\"x-moin/format;name=creole\"><page:arguments><page:argument page:name=\"style\">st: er</page:argument><page:argument page:name=\"class\">par: arg para: arga</page:argument></page:arguments><page:body>... **bold** ...</page:body></page:part></page:body></page:page>", u"""\n\n.. parser:creole style="st: er" class="par: arg para: arga"\n  ... **bold** ..."""),
        ]
        for i in data:
            yield (self.do, ) + i

coverage_modules = ['MoinMoin.converter.rst_out']
