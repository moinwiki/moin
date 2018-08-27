# Copyright: 2018 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for rst -> DOM -> rst using rst in and out converters

TODO: Failing tests are commented out and need to be fixed.
"""

import re

import pytest
import docutils

from emeraldtree import ElementTree as ET
from werkzeug.utils import unescape

try:
    from flask import g as flaskg
except ImportError:
    # in case converters become an independent package
    flaskg = None

from MoinMoin import config
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink, xinclude, html
from MoinMoin.constants.contenttypes import CHARSET

# ### TODO: try block (do not crash if we don't have docutils)
pytest.importorskip('docutils')
from docutils import nodes, utils, writers, core
from docutils.parsers.rst import Parser
from docutils.nodes import reference, literal_block
from docutils.parsers import rst
from docutils.parsers.rst import directives, roles

from MoinMoin.converter.rst_in import Converter as conv_in
from MoinMoin.converter.rst_out import Converter as conv_out


class TestConverter(object):

    input_namespaces = 'xmlns="{0}" xmlns:page="{1}" xmlns:xlink="{2}" xmlns:xinclude="{3}" xmlns:html="{4}"'.format(
        moin_page.namespace, moin_page.namespace, xlink.namespace, xinclude.namespace, html.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
        xinclude.namespace: 'xinclude',
        html.namespace: 'html',
    }
    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv_in = conv_in()
        self.conv_out = conv_out()

    data = [
        # output is not identical to input, but HTML out display is the same
        (u'=====\nTitle\n=====\n\nSubTitle\n========\n\nSection\n-------\n',
         '\n=====\nTitle\n=====\n\nSubTitle\n========\n\nSection\n=======\n'),
        (u'para\n\n=======\nSection\n=======\n\nSubsection\n==========\n\nSubsubection\n------------\n',
         'para\n\nSection\n=======\n\nSubsection\n----------\n\nSubsubection\n************\n'),
        # output identical to input
        (u'\n==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\nH2a\n===\n',
         u'\n==\nH1\n==\n\nH2\n==\n\nH3\n--\n\nH4\n**\n\nH5\n::\n\nH6\n++\n\nH2a\n===\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_headers(self, input, output):
        self.do(input, output)

    data = [
        (u'Text', 'Text\n'),
        (u"Text\n\nText\n", 'Text\n\nText\n'),
        (u"**strong**\n", "**strong**\n"),
        (u"*emphasis*\n", "*emphasis*\n"),
        # extraneous x required below to prevent IndexError, side effect of serializer
        (u"{{{{{x\nblockcode\n}}}}}\n", "{{{{{x\nblockcode\n}}}}}\n"),
        (u"--(stroke)--\n", '--(stroke)--\n'),
        (u"__underline__\n", '__underline__\n'),
        (u"~+larger+~\n", '~+larger+~\n'),
        (u"~-smaller-~\n", '~-smaller-~\n'),
        (u"^super^script\n", '^super^script\n'),
        (u",,sub,,script\n", ',,sub,,script\n'),
        (u"#ANY any", "#ANY any\n"),
        # line blocks
        ('\n| Lend us a couple of bob till Thursday.\n', '\n| Lend us a couple of bob till Thursday.\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        (u".. This is a comment", u"\n..\n This is a comment\n"),
        (u"..\n This is a comment", u"\n..\n This is a comment\n"),
        (u"..\n [and] this!", u"\n..\n [and] this!\n"),
        (u"..\n this:: too!", u"\n..\n this:: too!\n"),
        (u"..\n |even| this:: !", u"\n..\n |even| this:: !\n"),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_comments(self, input, output):
        self.do(input, output)

    data = [
        (u".. macro:: <<TableOfContents()>>", '\n\n.. contents::\n\n'),
        (u".. contents::", '\n\n.. contents::\n\n'),
        (u".. macro:: <<Include(MyPage)>>", '\n.. include:: MyPage\n'),
        (u".. include:: MyPage", '\n.. include:: MyPage\n'),
        (u".. macro:: <<RandomItem()>>", '\n.. macro:: <<RandomItem()>>\n'),
        (u".. macro:: <<RandomItem(5)>>", '\n.. macro:: <<RandomItem(5)>>\n'),
        (u".. macro:: <<Date>>", '\n.. macro:: <<Date()>>\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_macros(self, input, output):
        self.do(input, output)

    data = [
        # examples taken from http://docutils.sourceforge.net/docs/user/rst/quickref.html#explicit-markup
        # output is not identical to input, but HTML out display is the same
        (u'External hyperlinks, like Python_.\n\n.. _Python: http://www.python.org/',
         u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n'),
        (u'External hyperlinks, like `Python <http://www.python.org/>`_.',
         u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n'),
        (u'Internal crossreferences, like example_.\n\n.. _example:\n\nThis is an example crossreference target.',
         u'Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n'),
        (u'Python_ is `my favourite programming language`__.\n\n.. _Python: http://www.python.org/\n\n__ Python_',
         u'`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n'),
        (u'Titles are targets, too \n======================= \nImplict references, like `Titles are targets, too`_.',
         u'\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n'),
        # output is same as input
        (u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n',
         u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n'),
        (u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n',
         u'External hyperlinks, like `Python`_.\n\n\n.. _Python: http://www.python.org/\n\n'),
        (u'Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n',
         u'Internal crossreferences, like `example`_.\n\n.. _example:\n\nThis is an example crossreference target.\n'),
        (
        u'`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n',
        u'`Python`_ is `my favourite programming language`_.\n\n\n.. _Python: http://www.python.org/\n\n.. _my favourite programming language: http://www.python.org/\n\n'),
        (
        u'\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n',
        u'\n=======================\nTitles are targets, too\n=======================\n\nImplict references, like `Titles are targets, too`_.\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_link(self, input, output):
        self.do(input, output)

    data = [
        (u"- a\n- b\n\n  - aa\n  - ab\n",
         "\n* a\n* b\n\n  * aa\n  * ab\n"),
        (u"1. a\n#. b\n\n   (A) aa\n   (#) ab\n\n",
         "\n1. a\n#. b\n\n   A. aa\n   #. ab\n"),
        (u"1. a\n#. b\n\n   (A) aa\n   (#) ab\n",
         "\n1. a\n#. b\n\n   A. aa\n   #. ab\n"),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        # simple tables are converted to grid tables
        (u'== == ==\na  b  c  \n== == ==\n1  2  3\n== == ==', u'\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n'),
        (u'\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n', u'\n+-+-+-+\n|a|b|c|\n+=+=+=+\n|1|2|3|\n+-+-+-+\n\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        (
        u'.. image:: png\n   :height: 100\n   :width: 200\n   :scale: 50\n   :alt: alternate text png\n   :align: center',
        '\n.. image:: png\n   :height: 50\n   :width: 100\n   :alt: alternate text png\n   :align: center\n'),
        (
        u'.. figure:: png\n   :height: 100\n   :width: 200\n   :scale: 50\n   :alt: alternate text png\n\n   Moin Logo\n\n   This logo replaced the "MoinMoin Man"\n   logo long ago.\n',
        '\n.. figure:: png\n   :height: 50\n   :width: 100\n   :alt: alternate text png\n\n   Moin Logo\n\n   This logo replaced the "MoinMoin Man"\n   logo long ago.\n'),
    ]
    @pytest.mark.parametrize('input,output', data)
    def test_object(self, input, output):
        self.do(input, output)

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        return elem

    def serialize(self, elem, **options):
        from StringIO import StringIO
        buffer = StringIO()
        elem.write(buffer.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', buffer.getvalue())

    def do(self, input, output, args={}, skip=None):
        if skip:
            pytest.skip(skip)
        out = self.conv_in(input, 'text/x.moin.wiki;charset=utf-8', **args)
        out = self.conv_out(self.handle_input(self.serialize(out)), **args)
        assert self.handle_output(out) == output
        # ~ assert self.handle_output(out).strip() == output.strip()  # TODO: revert to above when number of \n between blocks in moinwiki_out.py is stable
