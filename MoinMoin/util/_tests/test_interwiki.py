# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:MicheleOrru
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.interwiki Tests
"""


from __future__ import absolute_import, division

import pytest
import tempfile
import os.path
import shutil

from MoinMoin.util.interwiki import split_interwiki, join_wiki, InterWikiMap
from MoinMoin._tests import wikiconfig


class TestInterWiki(object):
    class Config(wikiconfig.Config):
        interwiki_map = dict(Self='http://localhost:8080/', MoinMoin='http://moinmo.in/', )

    def testSplitWiki(self):
        tests = [('SomePage', ('Self', 'SomePage')),
                 ('OtherWiki:OtherPage', ('OtherWiki', 'OtherPage')),
                 (':OtherPage', ('', 'OtherPage')),
                 # broken ('/OtherPage', ('Self', '/OtherPage')),
                 # wrong interpretation ('MainPage/OtherPage', ('Self', 'MainPage/OtherPage')),
                ]
        for markup, (wikiname, pagename) in tests:
            assert split_interwiki(markup) == (wikiname, pagename)

    def testJoinWiki(self):
        tests = [(('http://example.org/', u'SomePage'), 'http://example.org/SomePage'),
                 (('http://example.org/?page=$PAGE&action=show', u'SomePage'), 'http://example.org/?page=SomePage&action=show'),
                 (('http://example.org/', u'Aktuelle\xc4nderungen'), 'http://example.org/Aktuelle%C3%84nderungen'),
                 (('http://example.org/$PAGE/show', u'Aktuelle\xc4nderungen'), 'http://example.org/Aktuelle%C3%84nderungen/show'),
                ]
        for (baseurl, pagename), url in tests:
            assert join_wiki(baseurl, pagename) == url


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
        assert InterWikiMap.from_string(s).iwmap == dict(foo='bar',
                                                                  ham='spam')
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
