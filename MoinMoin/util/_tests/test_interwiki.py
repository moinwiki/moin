# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.interwiki Tests
"""


from __future__ import absolute_import, division

import tempfile
import os.path
import shutil

import pytest
from flask import current_app as app

from MoinMoin.util.interwiki import split_interwiki, join_wiki, InterWikiMap, url_for_item, _split_namespace, split_fqname
from MoinMoin._tests import wikiconfig
from MoinMoin.constants.keys import CURRENT
from MoinMoin.app import before_wiki


class TestInterWiki(object):
    class Config(wikiconfig.Config):
        interwiki_map = {'Self': 'http://localhost:8080/',
                         'MoinMoin': 'http://moinmo.in/',
                         'OtherWiki': 'http://otherwiki.com/',
                         'OtherWiki/ns1': 'http://otherwiki.com/ns1/',
                         'OtherWiki/ns1/ns2': 'http://otherwiki.com/ns1/ns2/',
        }

    def test_url_for_item(self):
        before_wiki()
        revid = 'cdc431e0fc624d6fb8372152dcb66457'

        tests = [(('SomePage', '', '', '', CURRENT, 'frontend.show_item', False), '/SomePage'),
                 # Method signature to understand the tuple parameters
                 # (item_name, wiki_name='', namespace='', rev=CURRENT, endpoint='frontend.show_item', _external=False):
                 (('SomePage', '', '', '', CURRENT, 'frontend.show_item', True), 'http://localhost:8080/SomePage'),
                 (('SomePage', '', '', '', CURRENT, 'frontend.modify_item', False), '/+modify/SomePage'),
                 # FIXME if you set interwiki_map = dict(Self='http://localhost:8080', MoinMoin='http://moinmo.in/', ),
                 # the above line make it fails, it returns http://localhost/+modify/SomePage
                 # (('SomePage', '', '', CURRENT, 'frontend.modify_item', True), 'http://localhost:8080/+modify/SomePage'),
                 (('SomeRevID', '', 'revid', '', revid, 'frontend.show_item', False), '/+show/+{0}/%40revid/SomeRevID'.format(revid)),
                 (('SomePage', '', '', '', revid, 'frontend.show_item_meta', False), '/+meta/+{0}/SomePage'.format(revid)),
                 # Valid namespaces
                 (('SomePage', '', '', 'ns1', CURRENT, 'frontend.show_item', False), '/ns1/SomePage'),
                 (('SomeTag', '', 'tags', 'ns1', CURRENT, 'frontend.show_item', False), '/ns1/%40tags/SomeTag'),
                 (('SomePage', '', '', 'ns1/ns2', CURRENT, 'frontend.show_item', True), 'http://localhost:8080/ns1/ns2/SomePage'),
                 (('SomePage', '', '', 'ns1', CURRENT, 'frontend.modify_item', False), '/+modify/ns1/SomePage'),
                 (('SomePage', '', '', 'ns1/ns2', CURRENT, 'frontend.show_item_meta', True), 'http://localhost:8080/+meta/ns1/ns2/SomePage'),
                 (('SomePage', '', '', 'ns1', revid, 'frontend.show_item', False), '/+show/+{0}/ns1/SomePage'.format(revid)),
                 (('SomePage', '', '', 'ns1/ns2', revid, 'frontend.show_item_meta', False), '/+meta/+{0}/ns1/ns2/SomePage'.format(revid)),
                 (('SomeRevID', '', 'revid', 'ns1/ns2', CURRENT, 'frontend.show_item_meta', False), '/+meta/ns1/ns2/%40revid/SomeRevID'.format(revid)),

                 (('SomePage', 'MoinMoin', '', 'ns1', CURRENT, 'frontend.show_item', False), 'http://moinmo.in/ns1/SomePage'),
                 (('SomePage', 'MoinMoin', '', '', CURRENT, 'frontend.show_item', False), 'http://moinmo.in/SomePage'),
                 # FIXME will exist a map for this case? maybe there should be a placeholder for it.
                 # we need that for wiki farms with common search index and search in non-current revisions.
                 (('SomePage', 'MoinMoin', '', '', revid, 'frontend.show_item', False), 'http://moinmo.in/+show/+{0}/SomePage'.format(revid)),
                 (('SomeItemID', 'non-existent', 'itemid', '', CURRENT, 'frontend.show_item', False), '/non-existent/@itemid/SomeItemID'),
                 (('SomePage', 'non-existent', '', 'ns1', CURRENT, 'frontend.show_item', False), '/non-existent/ns1/SomePage'),
                ]

        for (item_name, wiki_name, field, namespace, rev, endpoint, _external), url in tests:
            assert url_for_item(item_name, wiki_name, field, namespace, rev, endpoint, _external) == url

    def test__split_namespace(self):
        map = set()
        map.add(u'ns1')
        map.add(u'ns1/ns2')
        tests = [('', ('', '')),
                 ('OtherWiki/', ('', 'OtherWiki/')),
                 ('ns1/', ('ns1', '')),
                 ('ns3/foo', ('', 'ns3/foo')),
                 ('ns1/OtherPage', ('ns1', 'OtherPage')),
                 ('ns1/ns2/OtherPage', ('ns1/ns2', 'OtherPage')),
                 ('ns1/ns2/ns1/ns2/OtherPage', ('ns1/ns2', 'ns1/ns2/OtherPage')),
                 ('SomePage', ('', 'SomePage')),
                 ('OtherWiki/ns1/OtherPage', ('', 'OtherWiki/ns1/OtherPage')),
                ]
        for markup, (namespace, pagename) in tests:
            assert _split_namespace(map, markup) == (namespace, pagename)
            namespace, pagename = _split_namespace(map, markup)

    def test_split_interwiki(self):
        app.cfg.namespace_mapping = [(u'', 'default_backend'), (u'ns1/', 'default_backend'), (u'ns1/ns2/', 'other_backend')]
        tests = [('', ('Self', '', 'name_exact', '')),
                 ('OtherWiki/', ('OtherWiki', '', 'name_exact', '')),
                 ('/ns1/', ('Self', 'ns1', 'name_exact', '')),
                 ('/@itemid/', ('Self', '', 'itemid', '')),
                 ('/ns3/foo', ('Self', '', 'name_exact', 'ns3/foo')),
                 ('@tags/SomeTag', ('Self', '', 'tags', 'SomeTag')),
                 ('OtherWiki/OtherPage', ('OtherWiki', '', 'name_exact', 'OtherPage')),
                 ('NonExistentWiki/OtherPage', ('Self', '', 'name_exact', 'NonExistentWiki/OtherPage')),
                 ('OtherWiki/ns1/@invalidID/Page', ('OtherWiki', 'ns1', 'name_exact', '@invalidID/Page')),
                 ('/ns1/OtherPage', ('Self', 'ns1', 'name_exact', 'OtherPage')),
                 ('/ns1/ns2/OtherPage', ('Self', 'ns1/ns2', 'name_exact', 'OtherPage')),
                 ('ns1/OtherPage', ('Self', 'ns1', 'name_exact', 'OtherPage')),
                 ('ns1/ns2/OtherPage', ('Self', 'ns1/ns2', 'name_exact', 'OtherPage')),
                 ('OtherWiki/ns1/OtherPage', ('OtherWiki', 'ns1', 'name_exact', 'OtherPage')),
                 ('OtherWiki/ns1/ns2/OtherPage', ('OtherWiki', 'ns1/ns2', 'name_exact', 'OtherPage')),
                 ('OtherWiki/ns1/ns2/@userid/SomeUserID', ('OtherWiki', 'ns1/ns2', 'userid', 'SomeUserID')),
                 ('OtherWiki/ns3/ns2/@Notfield/OtherPage/foo', ('OtherWiki', '', 'name_exact', 'ns3/ns2/@Notfield/OtherPage/foo')),
                ]
        for markup, (wikiname, namespace, field, pagename) in tests:
            assert split_interwiki(markup) == (wikiname, namespace, field, pagename)
            wikiname, namespace, field, pagename = split_interwiki(markup)
            assert isinstance(namespace, unicode)
            assert isinstance(pagename, unicode)
            assert isinstance(field, unicode)
            assert isinstance(wikiname, unicode)

    def testJoinWiki(self):
        tests = [(('http://example.org/', u'SomePage', '', ''), 'http://example.org/SomePage'),
                 (('', u'SomePage', '', ''), 'SomePage'),
                 (('http://example.org/?page=$PAGE&action=show', u'SomePage', '', ''), 'http://example.org/?page=SomePage&action=show'),
                 (('http://example.org/', u'Aktuelle\xc4nderungen', '', ''), 'http://example.org/Aktuelle%C3%84nderungen'),
                 (('http://example.org/$PAGE/show', u'Aktuelle\xc4nderungen', '', ''), 'http://example.org/Aktuelle%C3%84nderungen/show'),

                 (('http://example.org/', u'SomeItemID', 'itemid', u'ns1'), 'http://example.org/ns1/@itemid/SomeItemID'),
                 (('http://example.org/?page=$PAGE&action=show&namespace=$NAMESPACE', u'SomePage', '', u'ns1'), 'http://example.org/?page=SomePage&action=show&namespace=ns1'),
                 (('http://example.org/', u'Aktuelle\xc4nderungen', '', u'ns1\xc4'), 'http://example.org/ns1%C3%84/Aktuelle%C3%84nderungen'),
                 (('http://example.org/$NAMESPACE/$PAGE/show', u'Aktuelle\xc4nderungen', '', u'ns\xc41'), 'http://example.org/ns%C3%841/Aktuelle%C3%84nderungen/show'),
                 (('http://example.org/@$FIELD/$PAGE/show', u'Aktuelle\xc4nderungen', u'itemid', u''), 'http://example.org/@itemid/Aktuelle%C3%84nderungen/show'),
                ]
        for (baseurl, pagename, field, namespace), url in tests:
            assert join_wiki(baseurl, pagename, field, namespace) == url

    def test_split_fqname(self):
        app.cfg.namespace_mapping = [(u'', 'default_backend'), (u'ns1/', 'default_backend'), (u'ns1/ns2/', 'other_backend')]
        tests = [('ns1/ns2/@itemid/SomeItemID', ('ns1/ns2', 'itemid', 'SomeItemID')),
                 ('ns3/@itemid/SomeItemID', ('', 'name_exact', 'ns3/@itemid/SomeItemID')),
                 ('Page', ('', 'name_exact', 'Page')),
                 ('ns1/ns2/@tags/SomeTag', ('ns1/ns2', 'tags', 'SomeTag')),
                 ('@tags/SomeTag', ('', 'tags', 'SomeTag')),
                 ('ns1/ns2/@notid', ('ns1/ns2', 'name_exact', '@notid')),
                 ('ns1/ns2/ns3/Thisisapagename/ns4', ('ns1/ns2', 'name_exact', 'ns3/Thisisapagename/ns4')),
                ]
        for url, (namespace, field, pagename) in tests:
            assert split_fqname(url) == (namespace, field, pagename)


class TestInterWikiMapBackend(object):
    """
    tests for interwiki map
    """

    def test_load_file(self):
        """
        Test that InterWikiMap.from_file correctly loads file objects.
        """
        tmpdir = tempfile.mkdtemp()

        # test an invalid file
        with pytest.raises(IOError):
            InterWikiMap.from_file(os.path.join(tmpdir, 'void'))

        # test a consistent valid file
        testfile = os.path.join(tmpdir, 'foo.iwm')
        with open(testfile, 'w') as f:
            f.write('foo bar\n'
                    'baz spam\n'
                    'ham end end # this is really the end.')
        testiwm = InterWikiMap.from_file(testfile)
        assert testiwm.iwmap == dict(foo='bar', baz='spam', ham='end end')

        # test a malformed file
        testfile = os.path.join(tmpdir, 'bar.iwm')
        with open(testfile, 'w') as f:
            f.write('# This is a malformed interwiki file\n'
                    'fails # ever')
        with pytest.raises(ValueError):
            InterWikiMap.from_file(testfile)

        # finally destroy everything
        shutil.rmtree(tmpdir)

    def test_load_string(self):
        """
        Test that InterWikiMap.from_unicode correctly loads unicode objects.
        """
        # test for void wiki maps
        assert InterWikiMap.from_string(u'').iwmap == dict()
        assert InterWikiMap.from_string(u'#spam\r\n').iwmap == dict()
        # test for comments
        s = ('# foo bar\n'
             '#spamham\r\n'
             '#       space     space\n'
             'foo bar\r\n'
             'ham spam # this is a valid description')
        assert InterWikiMap.from_string(s).iwmap == dict(foo='bar', ham='spam')
        # test for valid strings
        s = ('link1 http://link1.com/\r\n'
             'link2 http://link2.in/\r\n')
        assert (InterWikiMap.from_string(s).iwmap ==
                dict(link1='http://link1.com/',
                     link2='http://link2.in/'))
        # test invalid strings
        with pytest.raises(ValueError):
            InterWikiMap.from_string(u'foobarbaz')

    def test_real_interwiki_map(self):
        """
        Test a 'real' interwiki file.
        """
        abspath = __file__.rsplit('MoinMoin')[0]
        testfile = os.path.join(abspath, 'contrib', 'interwiki', 'intermap.txt')
        testiwm = InterWikiMap.from_file(testfile)

        assert 'MoinSrc' in testiwm.iwmap
        assert testiwm.iwmap['MoinMaster'] == 'http://master.moinmo.in/'
        assert 'PythonInfo' in testiwm.iwmap
        assert 'this' not in testiwm.iwmap
        assert testiwm.iwmap['MoinCVS'] == 'http://hg.moinmo.in/moin/2.0?f=-1;file='


coverage_modules = ['MoinMoin.util.interwiki']
