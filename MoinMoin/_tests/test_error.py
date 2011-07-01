# -*- coding: utf-8 -*-
# Copyright: 2003-2004 by Nir Soffer <nirs AT freeshell DOT org>
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.error Tests
"""


import pytest

from MoinMoin import error


class TestEncoding(object):
    """ MoinMoin errors do work with unicode transparently """

    def testCreateWithUnicode(self):
        """ error: create with unicode """
        err = error.Error(u'טעות')
        assert unicode(err) == u'טעות'
        assert str(err) == 'טעות'

    def testCreateWithEncodedString(self):
        """ error: create with encoded string """
        err = error.Error('טעות')
        assert unicode(err) == u'טעות'
        assert str(err) == 'טעות'

    def testCreateWithObject(self):
        """ error: create with any object """
        class Foo:
            def __unicode__(self):
                return u'טעות'
            def __str__(self):
                return 'טעות'

        err = error.Error(Foo())
        assert unicode(err) == u'טעות'
        assert str(err) == 'טעות'

    def testAccessLikeDict(self):
        """ error: access error like a dict """
        test = 'value'
        err = error.Error(test)
        assert '%(message)s' % err == test

coverage_modules = ['MoinMoin.error']

