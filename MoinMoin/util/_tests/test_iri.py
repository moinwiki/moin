# -*- coding: utf-8 -*-
# Copyright: 2008,2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Tests for MoinMoin.util.iri
"""


import py.test

from MoinMoin.util.iri import *

def test_Iri_init_1():
    u = Iri(scheme='wiki', path='/StartSeite', query='action=raw')
    assert u.scheme == 'wiki'
    assert u.authority is None
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None

def test_Iri_init_2():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Iri(i, scheme='newwiki', path='/newStartSeite', query='action=false')
    assert u.scheme == 'newwiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/newStartSeite'
    assert u.query == 'action=false'
    assert u.fragment == 'body'

def test_Iri_init_3():
    i = Iri(scheme='wiki', path='/StartSeite', query='action=raw')
    u = Iri(i)
    assert i is not u
    assert i == u

def test_Iri_parser():
    i = 'http://moinmo.in/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite?action=raw'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:///StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:///StartSeite?action=raw'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:///StartSeite'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:///'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_2():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'wiki:///StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_3():
    i = 'wiki.local:StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki.local'
    assert u.authority is None
    assert u.path == 'StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_add_1():
    base = Iri('wiki://moinmo.in/Some/Page?action=raw#body')

    u = base + Iri('http://thinkmo.de/')
    assert u.scheme == 'http'
    assert u.authority == 'thinkmo.de'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('//thinkmo.de/')
    assert u.scheme == 'wiki'
    assert u.authority == 'thinkmo.de'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('/')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('/?action=edit')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
    assert u.query == 'action=edit'
    assert u.fragment is None

    u = base + Iri('')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=raw'
    assert u.fragment is None

    u = base + Iri('.')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('..')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('?action=edit')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=edit'
    assert u.fragment is None

    u = base + Iri('#head')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=raw'
    assert u.fragment == 'head'

def test_Iri_quote_1():
    u = Iri(scheme=u'wiki', authority=u'authority_ä%?#', path=u'/path_ä%?#', query=u'query_ä%?#', fragment=u'fragment_ä%?#')
    assert u.scheme == u'wiki'
    assert u.authority == u'authority_ä%?#'
    authority = u'authority_ä%25%3F%23'
    assert u.authority.fullquoted == authority
    assert u.authority.quoted == u'authority_ä%25?#'
    assert u.authority.urlquoted == u'authority_%C3%A4%25%3F%23'
    assert u.path == u'/path_ä%?#'
    path = u'/path_ä%25%3F%23'
    assert u.path.fullquoted == path
    assert u.path.quoted == u'/path_ä%25?#'
    assert u.path.urlquoted == u'/path_%C3%A4%25%3F%23'
    assert u.query == u'query_ä%?#'
    query = u'query_ä%25?%23'
    assert u.query.fullquoted == query
    assert u.query.quoted == u'query_ä%25?#'
    assert u.query.urlquoted == u'query_%C3%A4%25?%23'
    assert u.fragment == u'fragment_ä%?#'
    fragment = u'fragment_ä%25?%23'
    assert u.fragment.fullquoted == fragment
    assert u.fragment.quoted == u'fragment_ä%25?#'
    assert u.fragment.urlquoted == u'fragment_%C3%A4%25?%23'
    assert unicode(u) == u'wiki://%s%s?%s#%s' % (authority, path, query, fragment)

def test_Iri_quote_2():
    authority = u'authority_ä%25%3F%23'
    path = u'/path_ä%25%3F%23'
    query = u'query_ä%25?%23'
    fragment = u'fragment_ä%25?%23'
    i = u'wiki://%s%s?%s#%s' % (authority, path, query, fragment)
    u = Iri(i)
    assert unicode(u) == i

def test_Iri_quote_3():
    i = u'wiki:///path_%92%92'
    u = Iri(i)
    assert u.path.fullquoted == u'/path_%92%92'
    assert u.path.quoted == u'/path_%92%92'
    assert unicode(u) == i

def test_IriAuthority_parser_1():
    i = 'moinmo.in'
    u = IriAuthority(i)
    assert u.userinfo is None
    assert u.host == 'moinmo.in'
    assert u.port is None
    assert unicode(u) == i

def test_IriAuthority_parser_2():
    i = '@moinmo.in:'
    u = IriAuthority(i)
    assert u.userinfo == ''
    assert u.host == 'moinmo.in'
    assert u.port == 0
    assert unicode(u) == i

def test_IriAuthority_parser_3():
    i = 'test:test@moinmo.in:1234'
    u = IriAuthority(i)
    assert u.userinfo == 'test:test'
    assert u.host == 'moinmo.in'
    assert u.port == 1234
    assert unicode(u) == i

def test_IriPath_1():
    i = '/'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == i

def test_IriPath_2():
    i = '/.'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/./'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_3():
    i = '/..'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/../'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_4():
    i = '/test'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == 'test'
    assert unicode(u) == i

    i = '/test/'
    u = IriPath(i)
    assert len(u) == 3
    assert u[0] == ''
    assert u[1] == 'test'
    assert u[2] == ''
    assert unicode(u) == i

    i = '/test/..'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/test/../'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_5():
    i = '/test/test1/../../test2'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == 'test2'
    assert unicode(u) == '/test2'


