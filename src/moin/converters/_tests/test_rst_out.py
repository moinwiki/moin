# Copyright: 2010 MoinMoin:DmitryAndreev
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters.rst_out
"""

import pytest

from emeraldtree import ElementTree as ET

from . import XMLNS_RE, TAGSTART_RE

from moin.utils.tree import moin_page, xlink
from moin.converters.rst_out import Converter


class Base:
    input_namespaces = ns_all = (
        f'xmlns="{moin_page.namespace}" xmlns:page="{moin_page.namespace}" xmlns:xlink="{xlink.namespace}"'
    )
    output_namespaces = {moin_page.namespace: "page"}

    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        assert self.handle_output(out) == output


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    data = [
        ("<page:p>Text</page:p>", "Text\n"),
        ("<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", "Text\n\nText\n"),
        ("<page:separator />", "\n\n----\n\n"),
        ("<page:strong>strong</page:strong>", "**strong**"),
        ("<page:emphasis>emphasis</page:emphasis>", "*emphasis*"),
        ("<page:blockcode>blockcode</page:blockcode>", "\n::\n\n  blockcode\n\n"),
        ("<page:code>monospace</page:code>", "``monospace``"),
        (
            """<page:page><page:body><page:h page:outline-level="1">h1</page:h><page:h page:outline-level="2">h2</page:h><page:h page:outline-level="3">h3</page:h><page:h page:outline-level="4">h4</page:h><page:h page:outline-level="5">h5</page:h><page:h page:outline-level="6">h6</page:h></page:body></page:page>""",
            """\n==\nh1\n==\n\nh2\n==\n\nh3\n--\n\nh4\n**\n\nh5\n::\n\nh6\n++\n""",
        ),
        (
            '<page:page><page:body><page:p>H<page:span page:baseline-shift="sub">2</page:span>O</page:p><page:p>E = mc<page:span page:baseline-shift="super">2</page:span></page:p></page:body></page:page>',
            "H\\ :sub:`2`\\ O\n\nE = mc\\ :sup:`2`\\ \n",
        ),
        ("<page:page><page:body><page:p>H<page:span>2</page:span>O</page:p></page:body></page:page>", "H2O\n"),
        (
            '<page:page><page:body><page:div page:class="comment dashed">comment</page:div></page:body></page:page>',
            "\n..\n comment\n",
        ),
        (
            "<page><body><line-block><line-blk>Lend us a couple of bob till Thursday.</line-blk></line-block></body></page>",
            "\n| Lend us a couple of bob till Thursday.\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            "\n* A\n",
        ),
        (
            '<page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>',
            "\n1. A\n",
        ),
        (
            '<page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>',
            "\nI. A\n",
        ),
        (
            '<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>',
            "\n* A\n* B\n\n  1. C\n  #. D\n\n     I. E\n     #. F\n",
        ),
        (
            "<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>",
            "A\n  B\n  C\n  D\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned="2">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned="2">C</page:table-cell></page:table-row></page:table-body></page:table>',
            "\n+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n",
        ),
        (
            "<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>",
            "\n+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n",
        ),
        (
            '<page:page><page:body><page:table><page:table-header><page:table-row><page:table-cell><page:p>AAAAAAAAAAAAAAAAAA</page:p></page:table-cell><page:table-cell><page:p>BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB</page:p></page:table-cell></page:table-row></page:table-header><page:table-body><page:table-row><page:table-cell page:number-rows-spanned="2"><page:p>cell spanning 2 rows</page:p></page:table-cell><page:table-cell><page:p>cell in the 2nd column</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>cell in the 2nd column of the 2nd row</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned="2"><page:p>test</page:p></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned="2"><page:p>test</page:p></page:table-cell></page:table-row></page:table-body></page:table></page:body></page:page>',
            """\n+--------------------+-------------------------------------+
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

""",
        ),
        (
            '<page:table><page:table-body><page:table-row><page:table-cell page:number-cols-spanned="2"><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell page:number-cols-spanned="2"><page:p>1</page:p></page:table-cell></page:table-row></page:table-body></page:table>',
            "\n+------+-----+\n|**A** |**C**|\n+------+-----+\n|1     |     |\n+------+-----+\n\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>",
            "A\n\nB\n\nC\n\nD\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>",
            "\n+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>",
            "\n+-+-+\n|Z|A|\n| | |\n| |B|\n| | |\n| |C|\n| | |\n| |D|\n+-+-+\n\n",
        ),
        (
            "<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>",
            "\n+-+\n|Z|\n+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n",
        ),
        (
            '<page:page><page:body>A<page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p>A<page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>A</page:body></page:page>',
            "A\n* A\n\n  A\n* A\n\n  A\n\n  A\n* A\nA",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_p(self, input, output):
        self.do(input, output)

    data = [
        (
            "<page><body><table><table-body><table-row><table-cell><strong>Author:</strong></table-cell><table-cell>Test</table-cell></table-row><table-row><table-cell><strong>Version:</strong></table-cell><table-cell>1.17</table-cell></table-row><table-row><table-cell><strong>Copyright:</strong></table-cell><table-cell>c</table-cell></table-row><table-row><table-cell><strong>Test:</strong></table-cell><table-cell><p>t</p></table-cell></table-row></table-body></table></body></page>",
            """\n+--------------+----+
|**Author:**   |Test|
+--------------+----+
|**Version:**  |1.17|
+--------------+----+
|**Copyright:**|c   |
+--------------+----+
|**Test:**     |t   |
+--------------+----+

""",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_docutils_features(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:body><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p></page:body></page:page>',
            "Abra  [#]_ \n\n\n.. [#] arba\n\n",
        ),
        (
            '<page:page><page:body><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p><page:p>Abra <page:note page:note-class="footnote">arba</page:note></page:p><page:p>Abra <page:note page:note-class="footnote">arba</page:note><page:note page:note-class="footnote">arba</page:note></page:p></page:body></page:page>',
            "Abra  [#]_ \n\nAbra  [#]_ \n\nAbra  [#]_  [#]_ \n\n\n.. [#] arba\n\n.. [#] arba\n\n.. [#] arba\n\n.. [#] arba\n\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_note(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba</page:p></page:body></page:page>',
            "Abra `test`_ arba\n\n\n.. _test: http://python.org\n\n",
        ),
        (
            '<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba <page:a xlink:href="http://python.ru">test</page:a></page:p></page:body></page:page>',
            "Abra `test`_ arba `test`_\n\n\n.. _test: http://python.org\n\n.. _test: http://python.ru\n\n",
        ),
        (
            '<page:page><page:body><page:p>Abra <page:a xlink:href="http://python.org">test</page:a> arba <page:a xlink:href="http://python.ru">test</page:a> rbaa <page:a xlink:href="http://python.su">test</page:a></page:p></page:body></page:page>',
            "Abra `test`_ arba `test`_ rbaa `test`_\n\n\n.. _test: http://python.org\n\n.. _test: http://python.ru\n\n.. _test: http://python.su\n\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:body><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Author:</page:strong></page:table-cell><page:table-cell>Test</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Version:</page:strong></page:table-cell><page:table-cell>1.17</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Copyright:</page:strong></page:table-cell><page:table-cell>c</page:table-cell></page:table-row><page:table-row><page:table-cell><page:strong>Test:</page:strong></page:table-cell><page:table-cell><page:p>t</page:p></page:table-cell></page:table-row></page:table-body></page:table></page:list-item-body></page:list-item></page:list></page:body></page:page>',
            """\n* A

  +--------------+----+
  |**Author:**   |Test|
  +--------------+----+
  |**Version:**  |1.17|
  +--------------+----+
  |**Copyright:**|c   |
  +--------------+----+
  |**Test:**     |t   |
  +--------------+----+
""",
        ),
        (
            '<page:page><page:body><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>A</page:p><page:blockcode> test </page:blockcode></page:list-item-body></page:list-item></page:list></page:body></page:page>',
            "\n* A\n::\n\n     test \n\n",
        ),
        (
            "<page:page><page:body><page:table><page:table-body><page:table-row><page:table-cell><page:p><page:strong>A</page:strong></page:p><page:line_break /><page:p><page:strong>A</page:strong></page:p></page:table-cell><page:table-cell><page:strong>B</page:strong><page:line_break /><page:strong>B</page:strong></page:table-cell></page:table-row></page:table-body></page:table></page:body></page:page>",
            "\n+-----+-----+\n|**A**|**B**|\n|     |     |\n|**A**|**B**|\n+-----+-----+\n\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_mixed(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:object xlink:href="http://static.moinmo.in/logos/moinmoin.png" />',
            "\n\n..  image:: http://static.moinmo.in/logos/moinmoin.png\n\n",
        ),
        (
            '<page:object page:alt="alt text" xlink:href="http://static.moinmo.in/logos/moinmoin.png">alt text</page:object>',
            "|alt text|\n\n.. |alt text| image:: http://static.moinmo.in/logos/moinmoin.png\n\n",
        ),
        ('<page:object xlink:href="attachment:image.png" />', "\n\n..  image:: attachment:image.png\n\n"),
        (
            '<page:object page:alt="alt text" xlink:href="attachment:image.png">alt text</page:object>',
            "|alt text|\n\n.. |alt text| image:: attachment:image.png\n\n",
        ),
        (
            '<page:object page:alt="alt text" xlink:href="attachment:image.png?width=100&amp;height=150&amp;align=left" />',
            "|alt text|\n\n.. |alt text| image:: attachment:image.png\n  :width: 100\n  :height: 150\n  :align: left\n\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_object(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:tag><page:table-of-content page:outline-level="2" /></page:tag>',
            "\n\n.. contents::\n   :depth: 2\n\n",
        ),
        (
            '<page:part page:alt="&lt;&lt;Anchor(anchorname)&gt;&gt;" page:content-type="x-moin/macro;name=Anchor"><page:arguments>anchorname</page:arguments></page:part>',
            "\n.. macro:: <<Anchor(anchorname)>>\n",
        ),
        (
            '<page:part page:alt="&lt;&lt;MonthCalendar(,,12)&gt;&gt;" page:content-type="x-moin/macro;name=MonthCalendar"><page:arguments>,,12</page:arguments></page:part>',
            "\n.. macro:: <<MonthCalendar(,,12)>>\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_macros(self, input, output):
        self.do(input, output)

    data = [
        (
            '<page:page><page:body><page:part page:content-type="x-moin/format;name=creole"><page:arguments><page:argument page:name="style">st: er</page:argument><page:argument page:name="class">par: arg para: arga</page:argument></page:arguments><page:body>... **bold** ...</page:body></page:part></page:body></page:page>',
            """\n\n.. parser:creole style="st: er" class="par: arg para: arga"\n  ... **bold** ...""",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_parser(self, input, output):
        self.do(input, output)


coverage_modules = ["moin.converters.rst_out"]
