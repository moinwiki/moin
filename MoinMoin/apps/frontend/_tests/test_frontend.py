# -*- coding: utf-8 -*-
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - basic tests for frontend
"""

from StringIO import StringIO

from flask import url_for
from flask import g as flaskg
from werkzeug import ImmutableMultiDict, FileStorage

from MoinMoin.apps.frontend import views
from MoinMoin import user
from MoinMoin.util import crypto
from MoinMoin._tests import wikiconfig
import pytest

class TestFrontend(object):
    def _test_view(self, viewname, status='200 OK', data=['<html>', '</html>'], content_types=['text/html; charset=utf-8'], viewopts={}):
        print 'GET %s' % url_for(viewname, **viewopts)
        with self.app.test_client() as c:
            rv = c.get(url_for(viewname, **viewopts))
            assert rv.status == status
            for item in data:
                assert item in rv.data
            assert rv.headers['Content-Type'] in content_types
            return rv

    def _test_view_post(self, viewname, status='302 FOUND', content_type='text/html; charset=utf-8', data=['<html>', '</html>'], form={}, viewopts={}):
        print 'POST %s' % url_for(viewname, **viewopts)
        with self.app.test_client() as c:
            rv = c.post(url_for(viewname, **viewopts), data=form)
            assert rv.status == status
            assert rv.headers['Content-Type'] in content_type
            for item in data:
                assert item in rv.data

    def test_ajaxdelete(self):
        self._test_view_post('frontend.ajaxdelete', status='200 OK', content_type='application/json', data=['{', '}'], form=dict(
            comment='Test',
            itemnames='["DoesntExist"]',
            ), viewopts=dict(item_name='DoesntExist'))

    def test_ajaxdestroy(self):
        self._test_view_post('frontend.ajaxdestroy', status='200 OK', content_type='application/json', data=['{', '}'], form=dict(
            comment='Test',
            itemnames='["DoesntExist"]',
            ), viewopts=dict(item_name='DoesntExist'))

    def test_ajaxmodify(self):
        self._test_view_post('frontend.ajaxmodify', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_jfu_server(self):
        self._test_view_post('frontend.jfu_server', status='200 OK', data=['{', '}'], form=dict(
            data_file=FileStorage(StringIO("Hello, world"), filename='C:\\fakepath\\DoesntExist.txt', content_type='text/plain'),
            ), viewopts=dict(item_name='WillBeCreated'), content_type='application/json')

    def test_show_item(self):
        self._test_view('frontend.show_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_show_dom(self):
        self._test_view('frontend.show_dom', status='404 NOT FOUND', data=['<?xml', '>'], viewopts=dict(item_name='DoesntExist'), content_types=['text/xml; charset=utf-8'])

    def test_indexable(self):
        self._test_view('frontend.indexable', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_highlight_item(self):
        self._test_view('frontend.highlight_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_show_item_meta(self):
        self._test_view('frontend.show_item_meta', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_content_item(self):
        self._test_view('frontend.content_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_get_item(self):
        self._test_view('frontend.get_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_download_item(self):
        self._test_view('frontend.download_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_convert_item(self):
        self._test_view('frontend.convert_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_modify_item(self):
        self._test_view('frontend.modify_item', status='200 OK', viewopts=dict(item_name='DoesntExist'))

    def test_rename_item(self):
        self._test_view('frontend.rename_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_delete_item(self):
        self._test_view('frontend.delete_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_index(self):
        self._test_view('frontend.index', status='200 OK', viewopts=dict(item_name='DoesntExist'))

    def test_backrefs(self):
        self._test_view('frontend.backrefs', status='200 OK', viewopts=dict(item_name='DoesntExist'))

    def test_history(self):
        self._test_view('frontend.history', status='200 OK', viewopts=dict(item_name='DoesntExist'))

    def test_diff(self):
        self._test_view('frontend.diff', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_similar_names(self):
        self._test_view('frontend.similar_names', viewopts=dict(item_name='DoesntExist'))

    def test_sitemap(self):
        self._test_view('frontend.sitemap', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist'))

    def test_tagged_items(self):
        self._test_view('frontend.tagged_items', status='200 OK', viewopts=dict(tag='DoesntExist'))

    def test_root(self):
        self._test_view('frontend.index')

    def test_robots(self):
        self._test_view('frontend.robots', data=['Disallow:'], content_types=['text/plain; charset=utf-8'])

    def test_search(self):
        self._test_view('frontend.search')

    def test_revert_item(self):
        self._test_view('frontend.revert_item', status='404 NOT FOUND', viewopts=dict(item_name='DoesntExist', rev='000000'))

    def test_mychanges(self):
        self._test_view('frontend.mychanges', viewopts=dict(userid='000000'))

    def test_global_history(self):
        self._test_view('frontend.global_history')

    def test_wanted_items(self):
        self._test_view('frontend.wanted_items')

    def test_orphaned_items(self):
        self._test_view('frontend.orphaned_items')

    def test_quicklink_item(self):
        self._test_view('frontend.quicklink_item', status='302 FOUND', viewopts=dict(item_name='DoesntExist'), data=['<!DOCTYPE HTML'])

    def test_subscribe_item(self):
        self._test_view('frontend.subscribe_item', status='302 FOUND', viewopts=dict(item_name='DoesntExist'), data=['<!DOCTYPE HTML'])

    def test_register(self):
        self._test_view('frontend.register')

    def test_verifyemail(self):
        self._test_view('frontend.verifyemail', status='302 FOUND', data=['<!DOCTYPE HTML'])

    def test_lostpass(self):
        self._test_view('frontend.lostpass')

    def test_recoverpass(self):
        self._test_view('frontend.recoverpass')

    def test_login(self):
        self._test_view('frontend.login')

    def test_logout(self):
        self._test_view('frontend.logout', status='302 FOUND', data=['<!DOCTYPE HTML'])

    def test_usersettings(self):
        self._test_view('frontend.usersettings')

    def test_bookmark(self):
        self._test_view('frontend.bookmark', status='302 FOUND', data=['<!DOCTYPE HTML'])

    def test_diffraw(self):
        self._test_view('frontend.diffraw', data=[], viewopts=dict(item_name='DoesntExist'))

    def test_favicon(self):
        rv = self._test_view('frontend.favicon', content_types=['image/x-icon', 'image/vnd.microsoft.icon'], data=[])
        assert rv.data.startswith('\x00\x00') # "reserved word, should always be 0"

    def test_global_tags(self):
        self._test_view('frontend.global_tags')

class TestUsersettings(object):
    def setup_method(self, method):
        # Save original user
        self.saved_user = flaskg.user

        # Create anon user for the tests
        flaskg.user = user.User()

        self.user = None

    def teardown_method(self, method):
        """ Run after each test

        Remove user and reset user listing cache.
        """
        # Remove user file and user
        if self.user is not None:
            del self.user

        # Restore original user
        flaskg.user = self.saved_user

    def test_user_password_change(self):
        self.createUser(u'moin', u'Xiwejr622')
        flaskg.user = user.User(name=u'moin', password=u'Xiwejr622')
        form = self.fillPasswordChangeForm(u'Xiwejr622', u'Woodoo645', u'Woodoo645')
        valid = form.validate()
        assert valid # form data is valid

    def test_user_unicode_password_change(self):
        name = u'moin'
        password = u'__שם משתמש לא קיים__' # Hebrew

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, u'Woodoo645', u'Woodoo645')
        valid = form.validate()
        assert valid # form data is valid

    def test_user_password_change_to_unicode_pw(self):
        name = u'moin'
        password = u'Xiwejr622'
        new_password = u'__שם משתמש לא קיים__' # Hebrew

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)
        form = self.fillPasswordChangeForm(password, new_password, new_password)
        valid = form.validate()
        assert valid # form data is valid

    def test_fail_user_password_change_pw_mismatch(self):
        self.createUser(u'moin', u'Xiwejr622')
        flaskg.user = user.User(name=u'moin', password=u'Xiwejr622')
        form = self.fillPasswordChangeForm(u'Xiwejr622', u'Piped33', u'Woodoo645')
        valid = form.validate()
        # form data is invalid because password1 != password2
        assert not valid

    def test_fail_password_change(self):
        self.createUser(u'moin', u'Xiwejr622')
        flaskg.user = user.User(name=u'moin', password=u'Xiwejr622')
        form = self.fillPasswordChangeForm(u'Xinetd33', u'Woodoo645', u'Woodoo645')
        valid = form.validate()
        # form data is invalid because password_current != user.password
        assert not valid

    # Helpers ---------------------------------------------------------

    def fillPasswordChangeForm(self, current_password, password1, password2):
        """ helper to fill UserSettingsPasswordForm form
        """
        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password_current', current_password),
              ('usersettings_password_password1', password1),
              ('usersettings_password_password2', password2),
              ('usersettings_password_submit', u'Save')
           ]
        )
        form = FormClass.from_flat(request_form)
        return form

    def createUser(self, name, password, pwencoded=False, email=None):
        """ helper to create test user
        """
        # Create user
        self.user = user.User()
        self.user.name = name
        self.user.email = email
        if not pwencoded:
            password = crypto.crypt_password(password)
        self.user.enc_password = password

        # Validate that we are not modifying existing user data file!
        if self.user.exists():
            self.user = None
            pytest.skip("Test user exists, will not override existing user data file!")

        # Save test user
        self.user.save()

        # Validate user creation
        if not self.user.exists():
            self.user = None
            pytest.skip("Can't create test user")
