# Copyright: 2013 MoinMoin:RishabhRaj
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for moin.converters for different imagetypes
"""

import pytest

from emeraldtree import ElementTree as ET

from . import serialize

from moin.converters.html_out import ConverterPage


def run_test(tree_xml, output):
    tree = ET.XML(tree_xml)
    converter = ConverterPage()
    tree = converter(tree)
    assert serialize(tree, method="html") == output


@pytest.mark.parametrize("img_type", ["image/jpeg", "image/svg+xml", "image/png", "image/gif"])
def test_image(img_type):
    """Tests if a set of imagetypes, result inside an img tag"""
    tree_xml = (
        '<ns0:page ns0:page-href="wiki:///Home" xmlns:ns0="http://moinmo.in/namespaces/page" '
        'xmlns:ns1="http://www.w3.org/2001/XInclude" xmlns:ns2="http://www.w3.org/1999/xhtml" '
        'xmlns:ns3="http://www.w3.org/1999/xlink"><ns0:body><ns0:p ns2:data-lineno="1">'
        '<ns0:page ns2:class="moin-transclusion" ns0:page-href="wiki:///imagetest" ns2:data-href="/imagetest">'
        '<ns0:body><ns0:object ns3:href="/+get/+2882c905b2ab409fbf79cd05637a112d/imagetest" ns0:type="{0}" />'
        "</ns0:body></ns0:page></ns0:p></ns0:body></ns0:page>"
    )

    output = (
        '<div xmlns="http://www.w3.org/1999/xhtml"><p data-lineno="1"><span class="moin-transclusion" '
        'data-href="/imagetest"><img alt="imagetest" src="/+get/+2882c905b2ab409fbf79cd05637a112d/imagetest">'
        "</span></p></div>"
    )

    run_test(tree_xml.format(img_type), output)


def test_resize():
    """Tests if resize attributes convert to respective html tag resize attributes"""
    image_resize = (
        '<ns0:page xmlns:ns0="http://moinmo.in/namespaces/page" '
        'xmlns:ns2="http://www.w3.org/1999/xhtml" xmlns:ns3="http://www.w3.org/1999/xlink">'
        "<ns0:body><ns0:p><ns0:page>"
        '<ns0:body><ns0:object ns3:href="/+get/+2882c905b2ab409fbf79cd05637a112d/imagetest" '
        'ns2:height="10" ns2:width="10" ns0:type="image/jpeg" />'
        "</ns0:body></ns0:page></ns0:p></ns0:body></ns0:page>"
    )

    image_resize_out = (
        '<div xmlns="http://www.w3.org/1999/xhtml"><p><div><img alt="imagetest" height="10" '
        'src="/+get/+2882c905b2ab409fbf79cd05637a112d/imagetest" width="10">'
        "</div></p></div>"
    )

    run_test(image_resize, image_resize_out)
