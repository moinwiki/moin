# -*- coding: utf-8 -*-
# Copyright: 2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - basic tests for frontend
"""

from flask import g as flaskg
from werkzeug import ImmutableMultiDict

from MoinMoin.apps.frontend import views
from MoinMoin import user
from MoinMoin.util import crypto

class TestFrontend(object):
    def test_root(self):
        with self.app.test_client() as c:
            rv = c.get('/') # / redirects to front page
            assert rv.status == '302 FOUND'

    def test_robots(self):
        with self.app.test_client() as c:
            rv = c.get('/robots.txt')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/plain; charset=utf-8'
            assert 'Disallow:' in rv.data

    def test_favicon(self):
        with self.app.test_client() as c:
            rv = c.get('/favicon.ico')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'image/x-icon'
            assert rv.data.startswith('\x00\x00') # "reserved word, should always be 0"

    def test_404(self):
        with self.app.test_client() as c:
            rv = c.get('/DoesntExist')
            assert rv.status == '404 NOT FOUND'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data

    def test_global_index(self):
        with self.app.test_client() as c:
            rv = c.get('/+index')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data

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
            py.test.skip("Test user exists, will not override existing user data file!")

        # Save test user
        self.user.save()

        # Validate user creation
        if not self.user.exists():
            self.user = None
            py.test.skip("Can't create test user")


class TestViews(object):
    """
    Tester class for +backrefs, +orphans and +wanted views
    """
    class DummyItem(object):
        """
        Fake storage object, simulating the page item object from the storage
        """
        def __init__(self, name, revision):
            self.latest_revision = revision
            self.name = name

        def get_revision(self, *args, **kw):
            return self.latest_revision

    class DummyRevision(object):
        """
        Fake revision object, used for retrieving ITEMTRANSCLUSIONS and ITEMLINKS meta
        """
        def __init__(self, links, transclusions):
            self.links = links
            self.transclusions = transclusions

        def get(self, meta_name, *args, **kw):
            if meta_name == 'itemlinks':
                return self.links
            if meta_name == 'itemtransclusions':
                return self.transclusions

    def setup_class(self):
        # list of tuples
        # (page_name, links, transclusions)
        items = [('page1', ['page2', 'page3'], ['page2']),
                 ('page2',  ['page1', 'page3'], []),
                 ('page3', ['page5'], ['page1']),
                 ('page4', [], ['page5'])
                ]
        # we create the list of items
        self.items = []
        for item in items:
            revision = self.DummyRevision(item[1], item[2])
            page = self.DummyItem(item[0], revision)
            self.items.append(page)

    def test_orphans(self):
        expected_orphans = sorted(['page4'])
        result_orphans = sorted(views._orphans(self.items))

        assert result_orphans == expected_orphans

    def test_wanteds(self):
        expected_wanteds = {'page5': ['page3', 'page4']}
        result_wanteds = views._wanteds(self.items)

        assert result_wanteds == expected_wanteds

    def test_backrefs(self):
        expected_backrefs = sorted(['page1', 'page2'])
        result_backrefs = sorted(views._backrefs(self.items, 'page3'))

        assert result_backrefs == expected_backrefs

