# Copyright: 2013 MoinMoin:RishabhRaj
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.converter for different imagetypes
"""

import pytest

from emeraldtree import tree as ET

from MoinMoin.converter.html_out import ConverterPage


class TestImg(object):
    def setup_class(self):
        self.converter = ConverterPage()

    def testImage(self):
        tree_xml = ('<ns0:page ns0:page-href="wiki:///Home" xmlns:ns0="http://moinmo.in/namespaces/page" '
                    'xmlns:ns1="http://www.w3.org/2001/XInclude" xmlns:ns2="http://www.w3.org/1999/xhtml" '
                    'xmlns:ns3="http://www.w3.org/1999/xlink"><ns0:body><ns0:p ns2:data-lineno="1">'
                    '<ns0:page ns2:class="moin-transclusion" ns0:page-href="wiki:///imagetest" ns2:data-href="/imagetest">'
                    '<ns0:body><ns0:object ns3:href="/+get/+2882c905b2ab409fbf79cd05637a112d/imagetest" ns0:type="{0}" />'
                    '</ns0:body></ns0:page></ns0:p></ns0:body></ns0:page>')
        tests = [
            ('image/jpeg', 'img'),
            ('image/svg+xml', 'img'),
            ('image/png', 'img'),
            ('image/gif', 'img'),
        ]

        for imagetype, tag_expected in tests:
            self.runTest(tree_xml.format(imagetype), tag_expected)

    def runTest(self, tree_xml, tag_expected):
        tree = ET.XML(tree_xml)
        tree = self.converter(tree)
        assert len(tree) and len(tree[0]) and len(tree[0][0]) == 1
        assert tree[0][0][0].tag.name == tag_expected
