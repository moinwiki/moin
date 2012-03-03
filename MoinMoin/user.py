# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2003-2012 MoinMoin:ThomasWaldmann
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
from flask import session, request, url_for

from whoosh.query import Term, And, Or

from MoinMoin import wikiutil
from MoinMoin.config import CONTENTTYPE_USER
from MoinMoin.constants.keys import *
from MoinMoin.i18n import _, L_, N_
from MoinMoin.mail import sendmail
from MoinMoin.util.interwiki import getInterwikiHome, getInterwikiName, is_local_wiki
from MoinMoin.util.crypto import crypt_password, upgrade_password, valid_password, \
                                 generate_token, valid_token, make_uuid
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
    if validate and search_users(name_exact=username):
        return _("This user name already belongs to somebody else.")

    theuser.profile[NAME] = unicode(username)

    pw_checker = app.cfg.password_checker
    if validate and pw_checker:
        pw_error = pw_checker(username, password)
        if pw_error:
            return _("Password not acceptable: %(msg)s", msg=pw_error)

    try:
        theuser.set_password(password, is_encrypted)
    except UnicodeError as err:
        # Should never happen
        return "Can't encode password: %(msg)s" % dict(msg=str(err))

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
    if q.get('name_exact') and isinstance(q.get('name_exact'), list):
        q['name_exact'] = q['name_exact'][0]
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
            return ('email', userdata.email)
        elif userdata.name:
            interwiki = getInterwikiHome(userdata.name)
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
    username_allowedchars = "'@.-_" # ' for names like O'Brian or email addresses.
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
            if isinstance(v, (list, dict, set)): # mutable
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

        _name = name or auth_username

        itemid = uid
        if not itemid and auth_username:
            users = search_users(name_exact=auth_username)
            if users:
                itemid = users[0].meta[ITEMID]
        if not itemid and _name and _name != 'anonymous':
            users = search_users(name_exact=_name)
            if users:
                itemid = users[0].meta[ITEMID]
        if itemid:
            self.load_from_id(itemid, password)
        else:
            self.profile[ITEMID] = make_uuid()
            if _name:
                self.profile[NAME] = _name
            if password is not None:
                self.set_password(password)

        # "may" so we can say "if user.may.read(pagename):"
        if self._cfg.SecurityPolicy:
            self.may = self._cfg.SecurityPolicy(self)
        else:
            from MoinMoin.security import Default
            self.may = Default(self)

    def __repr__(self):
        return "<{0}.{1} at {2:#x} name:{3!r} itemid:{4!r} valid:{5!r} trusted:{6!r}>".format(
            self.__class__.__module__, self.__class__.__name__, id(self),
            self.name, self.itemid, self.valid, self.trusted)

    def __getattr__(self, name):
        """
        delegate some lookups into the .profile
        """
        if name in [NAME, DISABLED, ITEMID, ALIASNAME, ENC_PASSWORD, EMAIL, OPENID,
                    MAILTO_AUTHOR, SHOW_COMMENTS, RESULTS_PER_PAGE, EDIT_ON_DOUBLECLICK,
                    THEME_NAME, LOCALE, TIMEZONE, SUBSCRIBED_ITEMS, QUICKLINKS,
                   ]:
            return self.profile[name]
        else:
            return object.__getattr__(self, name)

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
        if not self.valid and not self.disabled or changed: # do we need to save/update?
            self.save() # yes, create/update user profile

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

        # check the password against the password hash
        if not valid_password(password, pw_hash):
            return False, False

        new_pw_hash = upgrade_password(password, pw_hash)
        if not new_pw_hash:
            return True, False

        data[ENC_PASSWORD] = new_pw_hash
        return True, True

    def set_password(self, password, is_encrypted=False):
        if not is_encrypted:
            password = crypt_password(password)
        self.profile[ENC_PASSWORD] = password

    def save(self, force=False):
        """
        Save user account data to user account file on disk.
        """
        exists = self.exists
        self.profile.save(force=force)

        if not self.disabled:
            self.valid = True

        if not exists:
            pass # XXX UserCreatedEvent
        else:
            pass #  XXX UserChangedEvent

    def getText(self, text):
        """ translate a text to the language of this user """
        return text # FIXME, was: self._request.getText(text, lang=self.language)


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
        trail = [i for i in trail if i != item_name] # avoid dupes
        trail.append(item_name) # append current item name at end
        trail = trail[-self._cfg.trail_size:] # limit trail length
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
        return flaskg.user.name == self.name

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

    def mail_password_recovery(self, cleartext_passwd=None):
        """ Mail a user who forgot his password a message enabling
            him to login again.
        """
        token = self.generate_recovery_token()

        text = _("""\
Somebody has requested to email you a password recovery link.

Please use the link below to change your password to a known value:

%(link)s

If you didn't forget your password, please ignore this email.

""", link=url_for('frontend.recoverpass',
                        username=self.name, token=token, _external=True))

        subject = _('[%(sitename)s] Your wiki password recovery link',
                    sitename=self._cfg.sitename or "Wiki")
        mailok, msg = sendmail.sendmail(subject, text, to=[self.email], mail_from=self._cfg.mail_from)
        return mailok, msg

    def mail_email_verification(self):
        """ Mail a user a link to verify his email address. """
        token = self.generate_recovery_token()

        text = _("""\
Somebody has created an account with this email address.

Please use the link below to verify your email address:

%(link)s

If you didn't create this account, please ignore this email.

""", link=url_for('frontend.verifyemail',
                        username=self.name, token=token, _external=True))

        subject = _('[%(sitename)s] Please verify your email address',
                    sitename=self._cfg.sitename or "Wiki")
        mailok, msg = sendmail.sendmail(subject, text, to=[self.email], mail_from=self._cfg.mail_from)
        return mailok, msg

