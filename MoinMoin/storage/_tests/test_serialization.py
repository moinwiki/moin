# Copyright: 2009-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - XML (de)serialization

    TODO: provide fresh backend per test class (or even per test method?).
    TODO: use xpath for testing (or any other way so sequence of metadata
          keys does not matter)
"""


import py

from StringIO import StringIO

from flask import flaskg

from MoinMoin._tests import become_trusted, update_item
from MoinMoin.storage.serialization import Entry, create_value_object, serialize, unserialize

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'


class TestSerializeRev(object):

    def test_serialize_rev(self):
        become_trusted()
        params = (u'foo1', 0, dict(m1=u"m1"), 'bar1')
        item = update_item(*params)
        rev = item.get_revision(0)
        xmlfile = StringIO()
        serialize(rev, xmlfile)
        xml = xmlfile.getvalue()
        expected = (XML_DECL +
                    '<revision revno="0">'
                    '<meta>'
                    '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                    '<entry key="sha1"><str>763675d6a1d8d0a3a28deca62bb68abd8baf86f3</str>\n</entry>\n'
                    '<entry key="m1"><str>m1</str>\n</entry>\n'
                    '<entry key="name"><str>foo1</str>\n</entry>\n'
                    '<entry key="size"><int>4</int>\n</entry>\n'
                    '<entry key="uuid"><str>foo1</str>\n</entry>\n'
                    '</meta>\n'
                    '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>\n'
                    '</revision>\n')
        assert expected == xml


class TestSerializeItem(object):

    def test_serialize_item(self):
        become_trusted()
        testparams = [
            (u'foo2', 0, dict(m1=u"m1r0"), 'bar2'),
            (u'foo2', 1, dict(m1=u"m1r1"), 'baz2'),
        ]
        for params in testparams:
            item = update_item(*params)
        xmlfile = StringIO()
        serialize(item, xmlfile)
        xml = xmlfile.getvalue()
        expected = (XML_DECL +
                    '<item name="foo2">'
                    '<meta></meta>\n'
                    '<revision revno="0">'
                    '<meta>'
                    '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                    '<entry key="sha1"><str>033c4846b506a4a48e32cdf54515c91d3499adb3</str>\n</entry>\n'
                    '<entry key="m1"><str>m1r0</str>\n</entry>\n'
                    '<entry key="name"><str>foo2</str>\n</entry>\n'
                    '<entry key="size"><int>4</int>\n</entry>\n'
                    '<entry key="uuid"><str>foo2</str>\n</entry>\n'
                    '</meta>\n'
                    '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>\n'
                    '</revision>\n'
                    '<revision revno="1">'
                    '<meta>'
                    '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                    '<entry key="sha1"><str>f91d8fc20a5de853e62105cc1ee0bf47fd7ded0f</str>\n</entry>\n'
                    '<entry key="m1"><str>m1r1</str>\n</entry>\n'
                    '<entry key="name"><str>foo2</str>\n</entry>\n'
                    '<entry key="size"><int>4</int>\n</entry>\n'
                    '<entry key="uuid"><str>foo2</str>\n</entry>\n'
                    '</meta>\n'
                    '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>\n'
                    '</revision>\n'
                    '</item>\n')
        assert expected == xml

class TestSerializeBackend(object):

    def test_serialize_backend(self):
        become_trusted()
        testparams = [
            (u'foo3', 0, dict(m1=u"m1r0foo3"), 'bar1'),
            (u'foo4', 0, dict(m1=u"m1r0foo4"), 'bar2'),
            (u'foo4', 1, dict(m1=u"m1r1foo4"), 'baz2'),
        ]
        for params in testparams:
            update_item(*params)
        xmlfile = StringIO()
        serialize(flaskg.storage, xmlfile)
        xml = xmlfile.getvalue()
        assert xml.startswith(XML_DECL + '<backend>')
        assert xml.endswith('</backend>\n')
        # this is not very precise testing:
        assert '<item name="foo3"><meta></meta>' in xml
        assert '<revision revno="0"><meta>' in xml
        assert '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>' in xml
        assert '<entry key="m1"><str>m1r0foo3</str>\n</entry>' in xml
        assert '<entry key="name"><str>foo3</str>\n</entry>' in xml
        assert '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>' in xml
        assert '<item name="foo4"><meta></meta>' in xml
        assert '<entry key="m1"><str>m1r0foo4</str>\n</entry>' in xml
        assert '<entry key="name"><str>foo4</str>\n</entry>' in xml
        assert '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>' in xml
        assert '<revision revno="1"><meta>' in xml
        assert '<entry key="m1"><str>m1r1foo4</str>\n</entry>' in xml
        assert '<entry key="name"><str>foo4</str>\n</entry>' in xml
        assert '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>' in xml


class TestSerializer2(object):
    def test_Entry(self):
        test_data = [
            ('foo', 'bar', '<entry key="foo"><bytes>bar</bytes>\n</entry>\n'),
            (u'foo', u'bar', '<entry key="foo"><str>bar</str>\n</entry>\n'),
            ('''<"a"&'b'>''', '<c&d>', '''<entry key="&lt;&quot;a&quot;&amp;'b'&gt;"><bytes>&lt;c&amp;d&gt;</bytes>\n</entry>\n'''),
        ]
        for k, v, expected_xml in test_data:
            e = Entry(k, v)
            xmlfile = StringIO()
            serialize(e, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == XML_DECL + expected_xml

        for expected_k, expected_v, xml in test_data:
            xmlfile = StringIO(xml)
            result = {}
            unserialize(Entry(attrs={'key': expected_k}, rev_or_item=result), xmlfile)
            assert expected_k in result
            assert result[expected_k] == expected_v

    def test_Values(self):
        test_data = [
            ('bar', '<bytes>bar</bytes>\n'),
            (u'bar', '<str>bar</str>\n'),
            (42, '<int>42</int>\n'),
            (True, '<bool>True</bool>\n'),
            (23.42, '<float>23.42</float>\n'),
            (complex(1.2, 2.3), '<complex>(1.2+2.3j)</complex>\n'),
            ((1, 2), '<tuple><int>1</int>\n<int>2</int>\n</tuple>\n'),
            ((1, u'bar'), '<tuple><int>1</int>\n<str>bar</str>\n</tuple>\n'),
            ((1, (u'bar', u'baz')), '<tuple><int>1</int>\n<tuple><str>bar</str>\n<str>baz</str>\n</tuple>\n</tuple>\n'),
        ]
        for v, expected_xml in test_data:
            v = create_value_object(v)
            xmlfile = StringIO()
            serialize(v, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == XML_DECL + expected_xml

