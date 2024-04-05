# Copyright: 2018 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for rst -> DOM -> rst using rst in and out converters

TODO: Failing tests are commented out and need to be fixed.
"""

import pytest

from emeraldtree import ElementTree as ET

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from . import serialize, XMLNS_RE, TAGSTART_RE

from moin.utils.tree import moin_page, xlink, xinclude, html

from moin.converters.rst_in import Converter as conv_in
from moin.converters.rst_out import Converter as conv_out

# ### TODO: try block (do not crash if we don't have docutils)
pytest.importorskip("docutils")  # noqa


class TestConverter:

    input_namespaces = 'xmlns="{}" xmlns:page="{}" xmlns:xlink="{}" xmlns:xinclude="{}" xmlns:html="{}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace
    )

    namespaces = {
        moin_page.namespace: "page",
        xlink.namespace: "xlink",
        xinclude.namespace: "xinclude",
        html.namespace: "html",
    }
    input_re = TAGSTART_RE
    output_re = XMLNS_RE

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        # output is not identical to input, but HTML out display is the same
        (
            "=====\nTitle\n=====\n\nSubTitle\n========\n\nSection\n-------\n",
            "\n=====\nTitle\n=====\n\nSubTitle\n========\n\nSection\n=======\n",
        ),
        (
            "para\n\n=======\nSection\n=======\n\nSubsection\n==========\n\nSubsubection\n------------\n",
            "para\n\nSection\n=======\n\nSubsection\n----------\n\nSubsubection\n************\n",
        ),
        # output identical to input
        (
            "\n==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\nH2a\n===\n",
            "\n==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\nH2a\n===\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_headers(self, input, output):
        self.do(input, output)

    data = [
        ("Text", "Text\n"),
        ("Text\n\nText\n", "Text\n\nText\n"),
        ("**strong**\n", "**strong**\n"),
        ("*emphasis*\n", "*emphasis*\n"),
        # extraneous x required below to prevent IndexError, side effect of serializer
        ("{{{{{x\nblockcode\n}}}}}\n", "{{{{{x\nblockcode\n}}}}}\n"),
        ("--(stroke)--\n", "--(stroke)--\n"),
        ("__underline__\n", "__underline__\n"),
        ("~+larger+~\n", "~+larger+~\n"),
        ("~-smaller-~\n", "~-smaller-~\n"),
        ("^super^script\n", "^super^script\n"),
        (",,sub,,script\n", ",,sub,,script\n"),
        ("#ANY any", "#ANY any\n"),
        # line blocks
        ("\n| Lend us a couple of bob till Thursday.\n", "\n| Lend us a couple of bob till Thursday.\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (".. This is a comment", "\n..\n This is a comment\n"),
        ("..\n This is a comment", "\n..\n This is a comment\n"),
        ("..\n [and] this!", "\n..\n [and] this!\n"),
        ("..\n this:: too!", "\n..\n this:: too!\n"),
        ("..\n |even| this:: !", "\n..\n |even| this:: !\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_comments(self, input, output):
        self.do(input, output)

    data = [
        (".. macro:: <<TableOfContents()>>", "\n\n.. contents::\n\n"),
        (".. contents::", "\n\n.. contents::\n\n"),
        (".. macro:: <<Include(MyPage)>>", "\n.. include:: MyPage\n"),
        (".. include:: MyPage", "\n.. include:: MyPage\n"),
        (".. macro:: <<RandomItem()>>", "\n.. macro:: <<RandomItem()>>\n"),
        (".. macro:: <<RandomItem(5)>>", "\n.. macro:: <<RandomItem(5)>>\n"),
        (".. macro:: <<Date>>", "\n.. macro:: <<Date()>>\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_macros(self, input, output):
        self.do(input, output)

    data = [
        # examples taken from http://docutils.sourceforge.net/docs/user/rst/quickref.html#explicit-markup
        # output is not identical to input, but HTML out display is the same
        (
            "External hyperlinks, like Python_.\n\n.. _Python: http://www.python.org/",
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
        ),
        (
            "External hyperlinks, like `Python <http://www.python.org/>`_.",
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
        ),
        (
            "Internal crossreferences, like example_.\n\n.. _example:\n\nThis is an example crossreference target.",
            "Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n",
        ),
        (
            "Python_ is `my favourite programming language`__.\n\n.. _Python: http://www.python.org/\n\n__ Python_",
            "`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n",
        ),
        (
            "Titles are targets, too \n======================= \nImplict references, like `Titles are targets, too`_.",
            "\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n",
        ),
        # output is same as input
        (
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
        ),
        (
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
            "External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n",
        ),
        (
            "Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n",
            "Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n",
        ),
        (
            "`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n",
            "`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n",
        ),
        (
            "\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n",
            "\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n",
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        ("- a\n- b\n\n  - aa\n  - ab\n", "\n* a\n* b\n\n  * aa\n  * ab\n"),
        ("1. a\n#. b\n\n   (A) aa\n   (#) ab\n\n", "\n1. a\n#. b\n\n   A. aa\n   #. ab\n"),
        ("1. a\n#. b\n\n   (A) aa\n   (#) ab\n", "\n1. a\n#. b\n\n   A. aa\n   #. ab\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        # simple tables are converted to grid tables
        ("== == ==\na  b  c  \n== == ==\n1  2  3\n== == ==", "\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n"),
        ("\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n", "\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
            ".. image:: png\n   :scale: 50\n   :alt: alternate text png\n   :align: center\n   :height: 100\n   :width: 200\n",
            "\n.. image:: png\n   :alt: alternate text png\n   :align: center\n   :height: 50\n   :width: 100\n",
        ),
        (
            '.. figure:: png\n   :alt: alternate text png\n   :height: 100\n   :width: 200\n   :scale: 50\n\n   Moin Logo\n\n   This logo replaced the "MoinMoin Man"\n   logo long ago.\n',
            '\n.. figure:: png\n   :alt: alternate text png\n   :height: 50\n   :width: 100\n\n   Moin Logo\n\n   This logo replaced the "MoinMoin Man"\n   logo long ago.\n',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_object(self, input, output):
        self.do(input, output)

    def handle_input(self, input):
        i = self.input_re.sub(r"\1 " + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, "text/x.moin.wiki;charset=utf-8", **args)
        out = self.conv_out(self.handle_input(self.serialize_strip(out)), **args)
        assert self.handle_output(out) == output
        # ~ assert self.handle_output(out).strip() == output.strip()  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
