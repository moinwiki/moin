# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2003-2013 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:JohannesBerg
# Copyright: 2007 MoinMoin:HeinrichWendel
# Copyright: 2008 MoinMoin:ChristopherDenter
# Copyright: 2010 MoinMoin:DiogenesAugusto
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - User Accounts

    TODO: Currently works on unprotected user backend

    This module contains functions to access user accounts (list all users, get
    some specific user). User instances are used to access the user profile of
    some specific user (name, password, email, bookmark, trail, settings, ...).
"""


from __future__ import absolute_import, division

import re
import copy
import hashlib
import werkzeug
from StringIO import StringIO

from babel import parse_locale

from flask import current_app as app
from flask import g as flaskg
from flask import session, request, url_for, render_template

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.constants.contenttypes import CONTENTTYPE_USER
from MoinMoin.constants.namespaces import NAMESPACE_USERPROFILES
from MoinMoin.constants.keys import *
from MoinMoin.constants.misc import ANON
from MoinMoin.i18n import _, L_, N_
from MoinMoin.mail import sendmail
from MoinMoin.util.interwiki import getInterwikiHome, getInterwikiName, is_local_wiki
from MoinMoin.util.crypto import generate_token, valid_token, make_uuid
from MoinMoin.storage.error import NoSuchItemError, ItemAlreadyExistsError, NoSuchRevisionError


def create_user(username, password, email, openid=None, validate=True, is_encrypted=False, is_disabled=False):
    """ create a user """
    # Create user profile
    theuser = User(auth_method="new-user")

    # Don't allow creating users with invalid names
    if validate and not isValidName(username):
        return _("""Invalid user name '%(name)s'.
Name may contain any Unicode alpha numeric character, with optional one
space between words. Group page name is not allowed.""", name=username)

    # Name required to be unique. Check if name belong to another user.
    if validate and search_users(**{NAME_EXACT: username}):
        return _("This user name already belongs to somebody else.")

    # XXX currently we just support creating with 1 name:
    theuser.profile[NAME] = [unicode(username), ]

    pw_checker = app.cfg.password_checker
    if validate and pw_checker:
        pw_error = pw_checker(username, password)
        if pw_error:
            return _("Password not acceptable: %(msg)s", msg=pw_error)

    theuser.set_password(password, is_encrypted)

    # try to get the email, for new users it is required
    if validate and not email:
        return _("Please provide your email address. If you lose your"
                 " login information, you can get it by email.")

    # Email should be unique - see also MoinMoin/script/accounts/moin_usercheck.py
    if validate and email and app.cfg.user_email_unique:
        if search_users(email=email):
            return _("This email already belongs to somebody else.")

    theuser.profile[EMAIL] = email

    # Openid should be unique
    if validate and openid and search_users(openid=openid):
        return _('This OpenID already belongs to somebody else.')

    theuser.profile[OPENID] = openid

    theuser.profile[DISABLED] = is_disabled

    # save data
    theuser.save()


def get_user_backend():
    return flaskg.unprotected_storage


def update_user_query(**q):
    USER_QUERY_STDARGS = {
        NAMESPACE: NAMESPACE_USERPROFILES,
        CONTENTTYPE: CONTENTTYPE_USER,
        WIKINAME: app.cfg.interwikiname,  # XXX for now, search only users of THIS wiki
                                          # maybe add option to not index wiki users
                                          # separately, but share them in the index also.
    }
    q.update(USER_QUERY_STDARGS)
    return q


def search_users(**q):
    """ Searches for a users with given query keys/values """
    # Since item name is a list, it's possible a list have been passed as parameter.
    # No problem, since user always have just one name (TODO: validate single name for user)
    if q.get(NAME_EXACT) and isinstance(q.get(NAME_EXACT), list):
        q[NAME_EXACT] = q[NAME_EXACT][0]
    q = update_user_query(**q)
    backend = get_user_backend()
    docs = backend.documents(**q)
    return list(docs)


def get_editor(userid, addr, hostname):
    """ Return a tuple of type id and string or Page object
        representing the user that did the edit.

        The type id is one of 'ip' (DNS or numeric IP), 'email' (email addr),
        'interwiki' (Interwiki homepage) or 'anon' ('').
    """
    result = 'anon', ''
    if app.cfg.show_hosts and hostname:
        result = 'ip', hostname
    if userid:
        userdata = User(userid)
        if userdata.mailto_author and userdata.email:
            return 'email', userdata.email
        elif userdata.name:
            interwiki = getInterwikiHome(userdata.name0)
            if interwiki:
                result = ('interwiki', interwiki)
    return result


def normalizeName(name):
    """ Make normalized user name

    Prevent impersonating another user with names containing leading,
    trailing or multiple whitespace, or using invisible unicode
    characters.

    Prevent creating user page as sub page, because '/' is not allowed
    in user names.

    Prevent using ':' and ',' which are reserved by acl.

    :param name: user name, unicode
    :rtype: unicode
    :returns: user name that can be used in acl lines
    """
    username_allowedchars = "'@.-_"  # ' for names like O'Brian or email addresses.
                                     # "," and ":" must not be allowed (ACL delimiters).
                                     # We also allow _ in usernames for nicer URLs.
    # Strip non alpha numeric characters (except username_allowedchars), keep white space
    name = ''.join([c for c in name if c.isalnum() or c.isspace() or c in username_allowedchars])

    # Normalize white space. Each name can contain multiple
    # words separated with only one space.
    name = ' '.join(name.split())

    return name


def isValidName(name):
    """ Validate user name

    :param name: user name, unicode
    """
    normalized = normalizeName(name)
    return (name == normalized) and not wikiutil.isGroupItem(name)


class UserProfile(object):
    """ A User Profile"""

    def __init__(self, **q):
        self._defaults = copy.deepcopy(app.cfg.user_defaults)
        self._meta = {}
        self._stored = False
        self._changed = False
        if q:
            self.load(**q)

    @property
    def stored(self):
        return self._stored

    def __getitem__(self, name):
        """
        get a value from the profile or,
        if not present, from the configured defaults
        """
        try:
            return self._meta[name]
        except KeyError:
            v = self._defaults[name]
            if isinstance(v, (list, dict, set)):  # mutable
                self._meta[name] = v
            return v

    def __setitem__(self, name, value):
        """
        set a value, update changed status
        """
        prev_value = self._meta.get(name)
        self._meta[name] = value
        if value != prev_value:
            self._changed = True

    def __delitem__(self, name):
        """
        delete a value, update changed status
        """
        del self._meta[name]
        self._changed = True

    def load(self, **q):
        """
        load a user profile, the query q can use any indexed (unique) field
        """
        q = update_user_query(**q)
        item = get_user_backend().existing_item(**q)
        rev = item[CURRENT]
        self._meta = dict(rev.meta)
        self._stored = True
        self._changed = False

    def save(self, force=False):
        """
        save a user profile (if it was changed since loading it)

        Note: if mutable profile values were modified, you need to use
              force=True because these changes are not detected!
        """
        if self._changed or force:
            self[NAMESPACE] = NAMESPACE_USERPROFILES
            self[CONTENTTYPE] = CONTENTTYPE_USER
            q = {ITEMID: self[ITEMID]}
            q = update_user_query(**q)
            item = get_user_backend().get_item(**q)
            item.store_revision(self._meta, StringIO(''), overwrite=True)
            self._stored = True
            self._changed = False


class User(object):
    """ A MoinMoin User """

    def __init__(self, uid=None, name="", password=None, auth_username="", trusted=False, **kw):
        """ Initialize User object

        :param uid: (optional) user ID (user itemid)
        :param name: (optional) user name
        :param password: (optional) user password (unicode)
        :param auth_username: (optional) already authenticated user name
                              (e.g. when using http basic auth) (unicode)
        :param trusted: (optional) whether user instance is created by a
                        trusted auth method / session
        :keyword auth_method: method that was used for authentication,
                              default: 'internal'
        :keyword auth_attribs: tuple of user object attribute names that are
                               determined by auth method and should not be
                               changeable by preferences, default: ().
                               First tuple element was used for authentication.
        """
        self.profile = UserProfile()
        self._cfg = app.cfg
        self.valid = False
        self.trusted = trusted
        self.auth_method = kw.get('auth_method', 'internal')
        self.auth_attribs = kw.get('auth_attribs', ())

        # XXX currently we just support creating with 1 name:
        _name = name or auth_username

        itemid = uid
        if not itemid and auth_username:
            users = search_users(**{NAME_EXACT: auth_username})
            if users:
                itemid = users[0].meta[ITEMID]
        if not itemid and _name and _name != ANON:
            users = search_users(**{NAME_EXACT: _name})
            if users:
                itemid = users[0].meta[ITEMID]
        if itemid:
            self.load_from_id(itemid, password)
        else:
            self.profile[ITEMID] = make_uuid()
            if _name:
                self.profile[NAME] = [_name, ]
            if password is not None:
                self.set_password(password)

        # "may" so we can say "if user.may.read(pagename):"
        self.may = self._cfg.SecurityPolicy(self)

    def __repr__(self):
        # In rare cases we might not have these profile settings when the __repr__ is called.
        name = getattr(self, NAME, [])
        itemid = getattr(self, ITEMID, None)

        return "<{0}.{1} at {2:#x} name:{3!r} itemid:{4!r} valid:{5!r} trusted:{6!r}>".format(
            self.__class__.__module__, self.__class__.__name__, id(self),
            name, itemid, self.valid, self.trusted)

    def __getattr__(self, name):
        """
        delegate some lookups into the .profile
        """
        if name in USEROBJ_ATTRS:
            try:
                return self.profile[name]
            except KeyError:
                raise AttributeError(name)
        else:
            raise AttributeError(name)

    @property
    def name0(self):
        try:
            names = self.name
            assert isinstance(names, list)
            return names[0]
        except IndexError:
            return ANON

    @property
    def language(self):
        l = self._cfg.language_default
        locale = self.locale  # is either None or something like 'en_US'
        if locale is not None:
            try:
                l = parse_locale(locale)[0]
            except ValueError:
                pass
        return l

    def avatar(self, size=30):
        if not app.cfg.user_use_gravatar:
            return None

        from MoinMoin.themes import get_current_theme
        from flask.ext.themes import static_file_url

        theme = get_current_theme()

        email = self.email
        if not email:
            return static_file_url(theme, theme.info.get('default_avatar', 'img/default_avatar.png'))

        param = {}
        param['gravatar_id'] = hashlib.md5(email.lower()).hexdigest()

        param['default'] = static_file_url(theme,
                                           theme.info.get('default_avatar', 'img/default_avatar.png'),
                                           True)

        param['size'] = str(size)
        # TODO: use same protocol of Moin site (might be https instead of http)]
        gravatar_url = "http://www.gravatar.com/avatar.php?"
        gravatar_url += werkzeug.url_encode(param)

        return gravatar_url

    def create_or_update(self, changed=False):
        """ Create or update a user profile

        :param changed: bool, set this to True if you updated the user profile values
        """
        if not self.valid and not self.disabled or changed:  # do we need to save/update?
            self.save()  # yes, create/update user profile

    def exists(self):
        """ Do we have a user profile for this user?

        :rtype: bool
        :returns: true, if we have a user account
        """
        return self.profile.stored

    def load_from_id(self, itemid, password=None):
        """ Load user account data from disk.

        :param password: If not None, then the given password must match the
                         password in the user account file.
        """
        try:
            self.profile.load(itemid=itemid)
        except (NoSuchItemError, NoSuchRevisionError):
            return

        # Validate data from user file. In case we need to change some
        # values, we set 'changed' flag, and later save the user data.
        changed = False

        if password is not None:
            # Check for a valid password, possibly changing storage
            valid, changed = self._validate_password(self.profile, password)
            if not valid:
                return

        if not self.disabled:
            self.valid = True

        # If user data has been changed, save fixed user data.
        if changed:
            self.profile.save()

    def _validate_password(self, data, password):
        """
        Check user password.

        This is a private method and should not be used by clients.

        :param data: dict with user data (from storage)
        :param password: password to verify [unicode]
        :rtype: 2 tuple (bool, bool)
        :returns: password is valid, enc_password changed
        """
        pw_hash = data[ENC_PASSWORD]

        # If we have no password set, we don't accept login with username.
        # Require non-empty password.
        if not pw_hash or not password:
            return False, False

        pwd_context = self._cfg.cache.pwd_context
        password_correct = False
        recomputed_hash = None
        try:
            password_correct, recomputed_hash = pwd_context.verify_and_update(password, pw_hash)
        except (ValueError, TypeError) as err:
            logging.error('in user profile %r, verifying the passlib pw hash raised an Exception [%s]' % (
                self.name, str(err)))
        else:
            if recomputed_hash is not None:
                data[ENC_PASSWORD] = recomputed_hash
        return password_correct, bool(recomputed_hash)

    def set_password(self, password, is_encrypted=False, salt=None):
        """
        Set or update the password (hash) stored for this user.

        :param password: the new password (or pw hash)
                         giving an empty string or None as password will invalidate the stored
                         password hash (meaning that it will not match against any given password)
        :param is_encrypted: if False (default), the password is given as plaintext and will be
                             "encrypted" (hashed) before getting stored.
                             if True, the already "encrypted" password hash is given in param
                             password and will be stored "as is" - this is mainly useful for tests.
        :param salt: if None (default), passlib will generate and use a random salt.
                     Otherwise, the given salt will be used - this is mainly useful for tests.
        """
        if not password:
            # invalidate the pw hash
            password = ''
        elif not is_encrypted:
            password = self._cfg.cache.pwd_context.encrypt(password, salt=salt)
        self.profile[ENC_PASSWORD] = password
        # Invalidate all other browser sessions except this one.
        session['user.session_token'] = self.generate_session_token(False)

    def has_invalidated_password(self):
        """
        Check if the password hash of this user is invalid.
        """
        return self.profile[ENC_PASSWORD] == ''

    def save(self, force=False):
        """
        Save user account data to user account file on disk.
        """
        exists = self.exists
        self.profile.save(force=force)

        if not self.disabled:
            self.valid = True

        if not exists:
            pass  # XXX UserCreatedEvent
        else:
            pass  # XXX UserChangedEvent

    def getText(self, text):
        """ translate a text to the language of this user """
        return text  # FIXME, was: self._request.getText(text, lang=self.language)

    # Bookmarks --------------------------------------------------------------

    def _set_bookmark(self, tm):
        """ Set bookmark timestamp.

        :param tm: timestamp (int or None)
        """
        if self.valid:
            if not (tm is None or isinstance(tm, int)):
                raise ValueError('tm should be int or None')
            if tm is None:
                self.profile[BOOKMARKS].pop(self._cfg.interwikiname)
            else:
                self.profile[BOOKMARKS][self._cfg.interwikiname] = tm
            self.save(force=True)

    def _get_bookmark(self):
        """ Get bookmark timestamp.

        :rtype: int / None
        :returns: bookmark timestamp or None
        """
        bm = None
        if self.valid:
            try:
                bm = self.profile[BOOKMARKS][self._cfg.interwikiname]
            except (ValueError, KeyError):
                pass
        return bm

    bookmark = property(_get_bookmark, _set_bookmark)

    # Subscribed Items -------------------------------------------------------

    def is_subscribed_to(self, pagelist):
        """ Check if user subscription matches any page in pagelist.

        The subscription contains interwiki page names. e.g 'WikiName:Page_Name'

        TODO: check if it's fast enough when getting called for many
              users from page.getSubscribersList()

        :param pagelist: list of pages to check for subscription
        :rtype: bool
        :returns: if user is subscribed any page in pagelist
        """
        if not self.valid:
            return False

        # Create a new list with interwiki names.
        pages = [getInterwikiName(pagename) for pagename in pagelist]
        # Create text for regular expression search
        text = '\n'.join(pages)

        for pattern in self.subscribed_items:
            # Try simple match first
            if pattern in pages:
                return True
            # Try regular expression search, skipping bad patterns
            try:
                pattern = re.compile(r'^{0}$'.format(pattern), re.M)
            except re.error:
                continue
            if pattern.search(text):
                return True

        return False

    def subscribe(self, pagename):
        """ Subscribe to a wiki page.

        Page names are saved as interwiki names.

        :param pagename: name of the page to subscribe
        :type pagename: unicode
        :rtype: bool
        :returns: if page was subscribed
        """
        pagename = getInterwikiName(pagename)
        subscribed_items = self.subscribed_items
        if pagename not in subscribed_items:
            subscribed_items.append(pagename)
            self.save(force=True)
            # XXX SubscribedToPageEvent
            return True
        return False

    def unsubscribe(self, pagename):
        """ Unsubscribe a wiki page.

        Try to unsubscribe by removing interwiki name from the subscription
        list.

        Its possible that the user will be subscribed to a page by more
        than one pattern. It can be both interwiki name and a regex pattern that
        both match the page. Therefore, we must check if the user is
        still subscribed to the page after we try to remove names from the list.

        :param pagename: name of the page to subscribe
        :type pagename: unicode
        :rtype: bool
        :returns: if unsubscribe was successful. If the user has a
            regular expression that matches, unsubscribe will always fail.
        """
        interWikiName = getInterwikiName(pagename)
        subscribed_items = self.profile[SUBSCRIBED_ITEMS]
        if interWikiName and interWikiName in subscribed_items:
            subscribed_items.remove(interWikiName)
            self.save(force=True)
        return not self.is_subscribed_to([pagename])

    # Quicklinks -------------------------------------------------------------

    def is_quicklinked_to(self, pagelist):
        """ Check if user quicklink matches any page in pagelist.

        :param pagelist: list of pages to check for quicklinks
        :rtype: bool
        :returns: if user has quicklinked any page in pagelist
        """
        if not self.valid:
            return False

        quicklinks = self.quicklinks
        for pagename in pagelist:
            interWikiName = getInterwikiName(pagename)
            if interWikiName and interWikiName in quicklinks:
                return True

        return False

    def quicklink(self, pagename):
        """ Adds a page to the user quicklinks

        Add links as interwiki names.

        :param pagename: page name
        :type pagename: unicode
        :rtype: bool
        :returns: if pagename was added
        """
        quicklinks = self.quicklinks
        interWikiName = getInterwikiName(pagename)
        if interWikiName and interWikiName not in quicklinks:
            quicklinks.append(interWikiName)
            self.save(force=True)
            return True
        return False

    def quickunlink(self, pagename):
        """ Remove a page from user quicklinks

        Remove interwiki name from quicklinks.

        :param pagename: page name
        :type pagename: unicode
        :rtype: bool
        :returns: if pagename was removed
        """
        quicklinks = self.quicklinks
        interWikiName = getInterwikiName(pagename)
        if interWikiName and interWikiName in quicklinks:
            quicklinks.remove(interWikiName)
            self.save(force=True)
            return True
        return False

    # Trail ------------------------------------------------------------------

    def add_trail(self, item_name):
        """ Add item name to trail.

        :param item_name: the item name (unicode) to add to the trail
        """
        item_name = getInterwikiName(item_name)
        trail_in_session = session.get('trail', [])
        trail = trail_in_session[:]
        trail = [i for i in trail if i != item_name]  # avoid dupes
        trail.append(item_name)  # append current item name at end
        trail = trail[-self._cfg.trail_size:]  # limit trail length
        if trail != trail_in_session:
            session['trail'] = trail

    def get_trail(self):
        """ Return list of recently visited item names.

        :rtype: list
        :returns: item names (unicode) in trail
        """
        return session.get('trail', [])

    # Other ------------------------------------------------------------------

    def is_current_user(self):
        """ Check if this user object is the user doing the current request """
        return flaskg.user.itemid == self.itemid

    # Sessions ---------------------------------------------------

    def logout_session(self, all_browsers=True):
        """ Terminate session in all browsers unless all_browsers is set to False """
        if all_browsers:
            self.generate_session_token(False)

        for key in ['user.itemid', 'user.trusted', 'user.auth_method', 'user.auth_attribs', 'user.session_token', ]:
            if key in session:
                del session[key]

    def generate_session_token(self, save=True):
        """ Generate new session token and key pair. Used to validate sessions. """
        key, token = generate_token()
        self.profile[SESSION_TOKEN] = token
        self.profile[SESSION_KEY] = key
        if save:
            self.save()

        return token

    def get_session_token(self):
        """ Get current session token. If there is no token, generate a new one. """
        try:
            return self.profile[SESSION_TOKEN]
        except KeyError:
            return self.generate_session_token()

    def validate_session(self, token):
        """ Check if the session token is valid.

        Invalid session tokens happen for these cases:
        a) there are multiple sessions (different machines, different browsers)
           open for same user. the user then changes the password in one of
           these, which creates a new session key in the profile also, which
           invalidates all sessions everywhere else for this user.
        b) the user profile is gone (e.g. due to erasing the storage), then
           a invalid session key will be read from the profile (from cfg.user_defaults)
           that will never validate against the session key read from the
           session.
        """
        # Ignore timeout, it's already handled by session cookie and session key should never timeout.
        return valid_token(self.profile[SESSION_KEY], token, None)

    # Account verification / Password recovery -------------------------------

    def generate_recovery_token(self):
        key, token = generate_token()
        self.profile[RECOVERPASS_KEY] = key
        self.save()
        return token

    def validate_recovery_token(self, token):
        return valid_token(self.profile[RECOVERPASS_KEY], token)

    def apply_recovery_token(self, token, newpass):
        if not self.validate_recovery_token(token):
            return False
        self.profile[RECOVERPASS_KEY] = None
        self.set_password(newpass)
        self.save()
        return True

    def mail_password_recovery(self, cleartext_passwd=None, subject=None, text=None):
        """ Mail a user who forgot his password a message enabling
            him to login again.
        """
        if not self.email:
            return False, "user has no E-Mail address in his profile."

        token = self.generate_recovery_token()

        if subject is None:
            subject = _('[%(sitename)s] Your wiki password recovery link', sitename='%(sitename)s')
        subject = subject % dict(sitename=self._cfg.sitename or "Wiki")
        if text is None:
            link = url_for('frontend.recoverpass', username=self.name0, token=token, _external=True)
            text = render_template('mail/password_recovery.txt', link=link)

        mailok, msg = sendmail.sendmail(subject, text, to=[self.email], mail_from=self._cfg.mail_from)
        return mailok, msg

    def mail_email_verification(self):
        """ Mail a user a link to verify his email address. """
        token = self.generate_recovery_token()

        link = url_for('frontend.verifyemail', username=self.name0, token=token, _external=True)
        text = render_template('mail/account_verification.txt', link=link)

        subject = _('[%(sitename)s] Please verify your email address',
                    sitename=self._cfg.sitename or "Wiki")
        mailok, msg = sendmail.sendmail(subject, text, to=[self.email], mail_from=self._cfg.mail_from)
        return mailok, msg
