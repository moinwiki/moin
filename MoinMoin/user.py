# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2003-2011 MoinMoin:ThomasWaldmann
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

import time
import copy

from babel import parse_locale

from flask import current_app as app
from flask import g as flaskg
from flask import session, request, url_for

from MoinMoin import config, wikiutil
from MoinMoin.i18n import _, L_, N_
from MoinMoin.util.interwiki import getInterwikiHome, is_local_wiki
from MoinMoin.util.crypto import crypt_password, upgrade_password, valid_password, \
                                 generate_token, valid_token



def create_user(username, password, email, openid=None):
    """ create a user """
    # Create user profile
    theuser = User(auth_method="new-user")

    theuser.name = username

    # Don't allow creating users with invalid names
    if not isValidName(theuser.name):
        return _("""Invalid user name '%(name)s'.
Name may contain any Unicode alpha numeric character, with optional one
space between words. Group page name is not allowed.""", name=theuser.name)

    # Name required to be unique. Check if name belong to another user.
    if getUserId(theuser.name):
        return _("This user name already belongs to somebody else.")

    pw_checker = app.cfg.password_checker
    if pw_checker:
        pw_error = pw_checker(theuser.name, password)
        if pw_error:
            return _("Password not acceptable: %(msg)s", msg=pw_error)

    # Encode password
    try:
        theuser.enc_password = crypt_password(password)
    except UnicodeError as err:
        # Should never happen
        return "Can't encode password: %(msg)s" % dict(msg=str(err))

    # try to get the email, for new users it is required
    theuser.email = email
    if not theuser.email:
        return _("Please provide your email address. If you lose your"
                 " login information, you can get it by email.")

    # Email should be unique - see also MoinMoin/script/accounts/moin_usercheck.py
    if theuser.email and app.cfg.user_email_unique:
        if get_by_email_address(theuser.email):
            return _("This email already belongs to somebody else.")

    # Openid should be unique
    theuser.openid = openid
    if theuser.openid and get_by_openid(theuser.openid):
            return _('This OpenID already belongs to somebody else.')

    # save data
    theuser.save()


def get_user_backend():
    """
    Just a shorthand that makes the rest of the code easier
    by returning the proper user backend.
    """
    ns_user_profile = app.cfg.ns_user_profile
    return flaskg.unprotected_storage.get_backend(ns_user_profile)


def getUserList():
    """ Get a list of all (numerical) user IDs.

    :rtype: list
    :returns: all user IDs
    """
    all_users = get_user_backend().iteritems()
    return [item.name for item in all_users]


def get_by_filter(key, value):
    """ Searches for an user with a given filter """
    from MoinMoin.storage.terms import ItemMetaDataMatch
    items = get_user_backend().search_items(ItemMetaDataMatch(key, value))
    users = [User(item.name) for item in items]
    return users


def get_by_email_address(email_address):
    """ Searches for an user with a particular e-mail address and returns it. """
    users = get_by_filter('email', email_address)
    if len(users) > 0:
        return users[0]

def get_by_openid(openid):
    """
    Searches for a user using an openid identifier.

    :param openid: the openid to filter with
    :type openid: unicode
    :returns: the user whose openid is this one
    :rtype: user object or None
    """
    users = get_by_filter('openid', openid)
    if len(users) > 0:
        return users[0]

def getUserId(searchName):
    """ Get the user ID for a specific user NAME.

    :param searchName: the user name to look up
    :rtype: string
    :returns: the corresponding user ID or None
    """
    from MoinMoin.storage.terms import ItemMetaDataMatch
    try:
        backend = get_user_backend()
        for user in backend.search_items(ItemMetaDataMatch('name', searchName)):
            return user.name
        return None
    except IndexError:
        return None


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


class User(object):
    """ A MoinMoin User """

    def __init__(self, uid=None, name="", password=None, auth_username="", **kw):
        """ Initialize User object

        :param uid: (optional) user ID
        :param name: (optional) user name
        :param password: (optional) user password (unicode)
        :param auth_username: (optional) already authenticated user name
                              (e.g. when using http basic auth) (unicode)
        :keyword auth_method: method that was used for authentication,
                              default: 'internal'
        :keyword auth_attribs: tuple of user object attribute names that are
                               determined by auth method and should not be
                               changeable by preferences, default: ().
                               First tuple element was used for authentication.
        """
        self._user_backend = get_user_backend()
        self._user = None

        self._cfg = app.cfg
        self.valid = 0
        self.id = uid
        self.auth_username = auth_username
        self.auth_method = kw.get('auth_method', 'internal')
        self.auth_attribs = kw.get('auth_attribs', ())
        self.bookmarks = {} # interwikiname: bookmark

        self.__dict__.update(copy.deepcopy(self._cfg.user_defaults))

        if name:
            self.name = name
        elif auth_username: # this is needed for user autocreate
            self.name = auth_username

        self.recoverpass_key = None

        if password:
            self.enc_password = crypt_password(password)

        self._stored = False
        self.last_saved = 0

        # attrs not saved to profile

        # we got an already authenticated username:
        check_password = None
        if not self.id and self.auth_username:
            self.id = getUserId(self.auth_username)
            if not password is None:
                check_password = password
        if self.id:
            self.load_from_id(check_password)
        elif self.name:
            self.id = getUserId(self.name)
            if self.id:
                # no password given should fail
                self.load_from_id(password or u'')
        # Still no ID - make new user
        if not self.id:
            self.id = self.make_id()
            if password is not None:
                self.enc_password = crypt_password(password)

        # "may" so we can say "if user.may.read(pagename):"
        if self._cfg.SecurityPolicy:
            self.may = self._cfg.SecurityPolicy(self)
        else:
            from MoinMoin.security import Default
            self.may = Default(self)

    def __repr__(self):
        return "<%s.%s at 0x%x name:%r valid:%r>" % (
            self.__class__.__module__, self.__class__.__name__,
            id(self), self.name, self.valid)

    @property
    def language(self):
        l = self._cfg.language_default
        # .locale is either None or something like 'en_US'
        if self.locale is not None:
            try:
                l = parse_locale(self.locale)[0]
            except ValueError:
                pass
        return l

    def make_id(self):
        """ make a new unique user id """
        #!!! this should probably be a hash of REMOTE_ADDR, HTTP_USER_AGENT
        # and some other things identifying remote users, then we could also
        # use it reliably in edit locking
        from random import randint
        return "%s.%d" % (str(time.time()), randint(0, 65535))

    def create_or_update(self, changed=False):
        """ Create or update a user profile

        :param changed: bool, set this to True if you updated the user profile values
        """
        if not self.valid and not self.disabled or changed: # do we need to save/update?
            self.save() # yes, create/update user profile

    def exists(self):
        """ Do we have a user account for this user?

        :rtype: bool
        :returns: true, if we have a user account
        """
        return self._user_backend.has_item(self.id)

    def load_from_id(self, password=None):
        """ Load user account data from disk.

        Can only load user data if the id number is already known.

        This loads all member variables, except "id" and "valid" and
        those starting with an underscore.

        :param password: If not None, then the given password must match the
                         password in the user account file.
        """
        if not self.exists():
            return

        self._user = self._user_backend.get_item(self.id)

        user_data = dict()
        for metadata_key in self._user:
            user_data[metadata_key] = self._user[metadata_key]

        # Validate data from user file. In case we need to change some
        # values, we set 'changed' flag, and later save the user data.
        changed = 0

        if password is not None:
            # Check for a valid password, possibly changing storage
            valid, changed = self._validatePassword(user_data, password)
            if not valid:
                return

        # Copy user data into user object
        for key, val in user_data.items():
            if isinstance(val, tuple):
                val = list(val)
            vars(self)[key] = val

        if not self.disabled:
            self.valid = 1

        # Mark this user as stored so saves don't send
        # the "user created" event
        self._stored = True

        # If user data has been changed, save fixed user data.
        if changed:
            self.save()

    def _validatePassword(self, data, password):
        """
        Check user password.

        This is a private method and should not be used by clients.

        :param data: dict with user data (from storage)
        :param password: password to verify [unicode]
        :rtype: 2 tuple (bool, bool)
        :returns: password is valid, enc_password changed
        """
        pw_hash = data['enc_password']

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

        data['enc_password'] = new_pw_hash
        return True, True

    def persistent_items(self):
        """ items we want to store into the user profile """
        nonpersistent_keys = ['id', 'valid', 'may', 'auth_username',
                              'password', 'password2',
                              'auth_method', 'auth_attribs', 'auth_trusted',
                             ]
        return [(key, value) for key, value in vars(self).items()
                    if key not in nonpersistent_keys and key[0] != '_' and value is not None]

    def save(self):
        """
        Save user account data to user account file on disk.

        This saves all member variables, except "id" and "valid" and
        those starting with an underscore.
        """
        if not self.exists():
            self._user = self._user_backend.create_item(self.id)
        else:
            self._user = self._user_backend.get_item(self.id)

        self._user.change_metadata()
        for key in self._user.keys():
            del self._user[key]

        self.last_saved = int(time.time())

        attrs = sorted(self.persistent_items())
        for key, value in attrs:
            if isinstance(value, list):
                value = tuple(value)
            self._user[key] = value

        self._user.publish_metadata()

        if not self.disabled:
            self.valid = 1

        if not self._stored:
            self._stored = True
            # XXX UserCreatedEvent
        else:
            pass #  XXX UserChangedEvent

    def getText(self, text):
        """ translate a text to the language of this user """
        return text # FIXME, was: self._request.getText(text, lang=self.language)


    # -----------------------------------------------------------------
    # Bookmark

    def setBookmark(self, tm):
        """ Set bookmark timestamp.

        :param tm: timestamp
        """
        if self.valid:
            interwikiname = self._cfg.interwikiname or u''
            self.bookmarks[interwikiname] = int(tm)
            self.save()

    def getBookmark(self):
        """ Get bookmark timestamp.

        :rtype: int
        :returns: bookmark timestamp or None
        """
        bm = None
        interwikiname = self._cfg.interwikiname or u''
        if self.valid:
            try:
                bm = self.bookmarks[interwikiname]
            except (ValueError, KeyError):
                pass
        return bm

    def delBookmark(self):
        """ Removes bookmark timestamp.

        :rtype: int
        :returns: 0 on success, 1 on failure
        """
        interwikiname = self._cfg.interwikiname or u''
        if self.valid:
            try:
                del self.bookmarks[interwikiname]
            except KeyError:
                return 1
            self.save()
            return 0
        return 1

    # -----------------------------------------------------------------
    # Subscribe

    def getSubscriptionList(self):
        """ Get list of pages this user has subscribed to

        :rtype: list
        :returns: pages this user has subscribed to
        """
        return self.subscribed_items

    def isSubscribedTo(self, pagelist):
        """ Check if user subscription matches any page in pagelist.

        The subscription list may contain page names or interwiki page
        names. e.g 'Page Name' or 'WikiName:Page_Name'

        TODO: check if it's fast enough when getting called for many
              users from page.getSubscribersList()

        :param pagelist: list of pages to check for subscription
        :rtype: bool
        :returns: if user is subscribed any page in pagelist
        """
        if not self.valid:
            return False

        import re
        # Create a new list with both names and interwiki names.
        pages = pagelist[:]
        if self._cfg.interwikiname:
            pages += [self._interWikiName(pagename) for pagename in pagelist]
        # Create text for regular expression search
        text = '\n'.join(pages)

        for pattern in self.getSubscriptionList():
            # Try simple match first
            if pattern in pages:
                return True
            # Try regular expression search, skipping bad patterns
            try:
                pattern = re.compile(r'^%s$' % pattern, re.M)
            except re.error:
                continue
            if pattern.search(text):
                return True

        return False

    def subscribe(self, pagename):
        """ Subscribe to a wiki page.

        To enable shared farm users, if the wiki has an interwiki name,
        page names are saved as interwiki names.

        :param pagename: name of the page to subscribe
        :type pagename: unicode
        :rtype: bool
        :returns: if page was subscribed
        """
        if self._cfg.interwikiname:
            pagename = self._interWikiName(pagename)

        if pagename not in self.subscribed_items:
            self.subscribed_items.append(pagename)
            self.save()

            # XXX SubscribedToPageEvent
            return True

        return False

    def unsubscribe(self, pagename):
        """ Unsubscribe a wiki page.

        Try to unsubscribe by removing non-interwiki name (leftover
        from old use files) and interwiki name from the subscription
        list.

        Its possible that the user will be subscribed to a page by more
        then one pattern. It can be both pagename and interwiki name,
        or few patterns that all of them match the page. Therefore, we
        must check if the user is still subscribed to the page after we
        try to remove names from the list.

        :param pagename: name of the page to subscribe
        :type pagename: unicode
        :rtype: bool
        :returns: if unsubscrieb was successful. If the user has a
            regular expression that match, it will always fail.
        """
        changed = False
        if pagename in self.subscribed_items:
            self.subscribed_items.remove(pagename)
            changed = True

        interWikiName = self._interWikiName(pagename)
        if interWikiName and interWikiName in self.subscribed_items:
            self.subscribed_items.remove(interWikiName)
            changed = True

        if changed:
            self.save()
        return not self.isSubscribedTo([pagename])

    # -----------------------------------------------------------------
    # Quicklinks

    def getQuickLinks(self):
        """ Get list of pages this user wants in the navibar

        :rtype: list
        :returns: quicklinks from user account
        """
        return self.quicklinks

    def isQuickLinkedTo(self, pagelist):
        """ Check if user quicklink matches any page in pagelist.

        :param pagelist: list of pages to check for quicklinks
        :rtype: bool
        :returns: if user has quicklinked any page in pagelist
        """
        if not self.valid:
            return False

        for pagename in pagelist:
            if pagename in self.quicklinks:
                return True
            interWikiName = self._interWikiName(pagename)
            if interWikiName and interWikiName in self.quicklinks:
                return True

        return False

    def addQuicklink(self, pagename):
        """ Adds a page to the user quicklinks

        If the wiki has an interwiki name, all links are saved as
        interwiki names. If not, as simple page name.

        :param pagename: page name
        :type pagename: unicode
        :rtype: bool
        :returns: if pagename was added
        """
        changed = False
        interWikiName = self._interWikiName(pagename)
        if interWikiName:
            if pagename in self.quicklinks:
                self.quicklinks.remove(pagename)
                changed = True
            if interWikiName not in self.quicklinks:
                self.quicklinks.append(interWikiName)
                changed = True
        else:
            if pagename not in self.quicklinks:
                self.quicklinks.append(pagename)
                changed = True

        if changed:
            self.save()
        return changed

    def removeQuicklink(self, pagename):
        """ Remove a page from user quicklinks

        Remove both interwiki and simple name from quicklinks.

        :param pagename: page name
        :type pagename: unicode
        :rtype: bool
        :returns: if pagename was removed
        """
        changed = False
        interWikiName = self._interWikiName(pagename)
        if interWikiName and interWikiName in self.quicklinks:
            self.quicklinks.remove(interWikiName)
            changed = True
        if pagename in self.quicklinks:
            self.quicklinks.remove(pagename)
            changed = True

        if changed:
            self.save()
        return changed

    def _interWikiName(self, pagename):
        """ Return the inter wiki name of a page name

        :param pagename: page name
        :type pagename: unicode
        """
        if not self._cfg.interwikiname:
            return None

        return "%s:%s" % (self._cfg.interwikiname, pagename)

    # -----------------------------------------------------------------
    # Trail

    def addTrail(self, item_name):
        """ Add item name to trail.

        :param item_name: the item name (unicode) to add to the trail
        """
        # Save interwiki links internally
        if self._cfg.interwikiname:
            item_name = self._interWikiName(item_name)
        trail_in_session = session.get('trail', [])
        trail = trail_in_session[:]
        trail = [i for i in trail if i != item_name] # avoid dupes
        trail.append(item_name) # append current item name at end
        trail = trail[-self._cfg.trail_size:] # limit trail length
        if trail != trail_in_session:
            session['trail'] = trail

    def getTrail(self):
        """ Return list of recently visited item names.

        :rtype: list
        :returns: item names (unicode) in trail
        """
        return session.get('trail', [])

    # -----------------------------------------------------------------
    # Other

    def isCurrentUser(self):
        """ Check if this user object is the user doing the current request """
        return flaskg.user.name == self.name

    def host(self):
        """ Return user host """
        host = self.isCurrentUser() and self._cfg.show_hosts and request.remote_addr
        return host or _("<unknown>")

    def wikiHomeLink(self):
        """ Return wiki markup usable as a link to the user homepage,
            it doesn't matter whether it already exists or not.
        """
        wikiname, pagename = getInterwikiHome(self.name)
        if is_local_wiki(wikiname):
            markup = '[[%s]]' % pagename
        else:
            markup = '[[%s:%s]]' % (wikiname, pagename)
        return markup

    def signature(self):
        """ Return user signature using wiki markup

        Users sign with a link to their homepage.
        Visitors return their host address.

        TODO: The signature use wiki format only, for example, it will
        not create a link when using rst format. It will also break if
        we change wiki syntax.
        """
        if self.name:
            return self.wikiHomeLink()
        else:
            return self.host()

    def generate_recovery_token(self):
        key, token = generate_token()
        self.recoverpass_key = key
        self.save()
        return token

    def apply_recovery_token(self, token, newpass):
        if not valid_token(self.recoverpass_key, token):
            return False
        self.recoverpass_key = None
        self.enc_password = crypt_password(newpass)
        self.save()
        return True

    def mailAccountData(self, cleartext_passwd=None):
        """ Mail a user who forgot his password a message enabling
            him to login again.
        """
        from MoinMoin.mail import sendmail
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
        mailok, msg = sendmail.sendmail([self.email], subject, text, mail_from=self._cfg.mail_from)
        return mailok, msg

