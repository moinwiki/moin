# -*- coding: utf-8 -*-
# Copyright: 2003-2004 by Nir Soffer <nirs AT freeshell DOT org>
# Copyright: 2007 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.error Tests
"""


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

        class Foo(object):
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
        assert '%(message)s' % dict(message=err) == test


class TestCompositeError(object):

    def setup_method(self, method):
        self.CompositeError_obj = error.CompositeError(error.InternalError)

    def teardown_method(self, method):
        self.CompositeError_obj.innerException = None

    def test_exceptions(self):
        self.CompositeError_obj.innerException = 'test_error1', 'test_error2', 'test_error3'
        result = error.CompositeError.exceptions(self.CompositeError_obj)
        expected = [('test_error1', 'test_error2', 'test_error3')]
        assert expected == result
        self.CompositeError_obj.innerException = str(error.InternalError(''))

    def test_subclasses(self):
        self.CompositeError_obj.innerException = str(error.FatalError('This is an internal Error'))
        result = error.CompositeError.exceptions(self.CompositeError_obj)
        expected = ['This is an internal Error']
        assert result == expected

        self.CompositeError_obj.innerException = str(error.FatalError('This is a fatal Error'))
        result = error.CompositeError.exceptions(self.CompositeError_obj)
        expected = ['This is a fatal Error']
        assert result == expected


coverage_modules = ['MoinMoin.error']
