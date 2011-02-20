"""
MoinMoin - Tests for MoinMoin.converter._args

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter._args import *

def test_Arguments___init__():
    positional = []
    keyword = {}

    a = Arguments(positional, keyword)

    assert positional == a.positional
    assert positional is not a.positional
    assert keyword == a.keyword
    assert keyword is not a.keyword

def test_Arguments___contains__():
    positional = ['positional', 'both']
    keyword = {'keyword': None, 'both': None}

    a = Arguments(positional, keyword)

    assert 'positional' in a
    assert 'keyword' in a
    assert 'both' in a
    assert 'none' not in a

def test_Arguments___getitem__():
    positional = ['positional', 'both']
    keyword = {'keyword': None, 'both': None}

    a = Arguments(positional, keyword)

    assert a[0] == 'positional'
    assert a[1] == 'both'
    assert a[:] == positional
    assert a['keyword'] is None
    assert a['both'] is None

    py.test.raises(IndexError, a.__getitem__, 2)
    py.test.raises(KeyError, a.__getitem__, 'none')

def test_Arguments___len__():
    positional = ['positional', 'both']
    keyword = {'keyword': None, 'both': None}

    a = Arguments(positional, keyword)

    assert len(a) == 4

def test_Arguments_items():
    positional = ['positional', 'both']
    keyword = {'keyword': True, 'both': False}

    a = Arguments(positional, keyword)

    l = list(a.items())

    assert len(l) == 4
    assert l[0] == (None, 'positional')
    assert l[1] == (None, 'both')
    assert ('keyword', True) in l
    assert ('both', False) in l

def test_Arguments_keys():
    positional = ['positional', 'both']
    keyword = {'keyword': True, 'both': False}

    a = Arguments(positional, keyword)

    l = list(a.keys())

    assert len(l) == 2
    assert 'keyword' in l
    assert 'both' in l

def test_Arguments_values():
    positional = ['positional', 'both']
    keyword = {'keyword': True, 'both': False}

    a = Arguments(positional, keyword)

    l = list(a.values())

    assert len(l) == 4
    assert l[0] == 'positional'
    assert l[1] == 'both'
    assert True in l
    assert False in l

