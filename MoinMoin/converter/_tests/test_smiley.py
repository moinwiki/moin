"""
MoinMoin - Tests for MoinMoin.converter.smiley

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details
"""

import re
import py

from MoinMoin.converter.smiley import Converter, moin_page, ET


def pytest_generate_tests(metafunc):
    for name, (input, query) in sorted(test_data.items()):
        metafunc.addcall(id=name, funcargs={'input': input, 'query': query})

output_namespaces = {
    moin_page.namespace: '',
}

input_re = re.compile(r'^(<[a-z:]+)')
output_re = re.compile(r'\s+xmlns="[^"]+"')


test_data = {
    'normal': (
        '<page><body><p>bla bla :-) bla bla</p></body></page>',
        '/page/body/p/span[@class="moin-text-icon moin-smile"]'),
    'in code': (
        '<page><body><code>bla bla :-) bla bla</code></body></page>',
        '/page/body[code="bla bla :-) bla bla"]'),
    '2 at once': (
        '<page><body><p>:-) :-(</p></body></page>',
        '/page/body/p'
            '[span[1][@class="moin-text-icon moin-smile"]]'
            '[span[2][@class="moin-text-icon moin-sad"]]'),
    'strong': (
        '<page><body><p><strong>:-)</strong></p></body></page>',
        '/page/body/p/strong/span[@class="moin-text-icon moin-smile"]'),
    # Test to check we do not have bug with newline in the string
    'ok with newlines': (
        '<page><body><p>1\n2\n3\n4</p></body></page>',
        '/page/body[p="1\n2\n3\n4"]'),
    # Test with space between the elements
    'space between elem': (
        '<page><body><table-of-content />     <p>text</p></body></page>',
        '/page/body[p="text"]'),
    # Test the ignored tags
    'ignored tag': (
        '<page><body><p><code>:-)</code></p></body></page>',
        '/page/body/p[code=":-)"]'),
    # Test the ignored tags and subelement
    'ignored tag and subelem': (
        '<page><body><blockcode>:-)<strong>:-(</strong>'
        '</blockcode></body></page>',
        '/page/body/blockcode[text()=":-)"][strong=":-("]'),
}


def ET_to_string(elem, **options):
    data = []
    elem.write(data.append, namespaces=output_namespaces)
    return output_re.sub(u'', ''.join(data))


def test_smiley_convert(input, query):
    etree = py.test.importorskip('lxml.etree')
    conv = Converter()
    print 'input:', input
    out_elem = conv(ET.XML(input))
    after_conversion = ET_to_string(out_elem)
    print 'output:', after_conversion
    print 'query:', query
    tree = etree.fromstring(after_conversion)
    result = tree.xpath(query)
    print 'query result:', result
    assert result
