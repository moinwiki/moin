# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2003-2008,2011 MoinMoin:ThomasWaldmann
# Copyright: 2003 Gustavo Niemeyer
# Copyright: 2005 Oliver Graf
# Copyright: 2007 Alexander Schremmer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Wiki Security Interface and Access Control Lists


This implements the basic interface for user permissions and
system policy. If you want to define your own policy, inherit
from the base class 'Permissions', so that when new permissions
are defined, you get the defaults.

Then assign your new class to "SecurityPolicy" in wikiconfig;
and I mean the class, not an instance of it!
"""


from functools import wraps

from flask import current_app as app
from flask import g as flaskg
from flask import abort

from MoinMoin import user
from MoinMoin.i18n import _, L_, N_


def require_permission(permission):
    """
    view decorator to require a specific permission

    if the permission is not granted, abort with 403
    """
    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kw):
            has_permission = getattr(flaskg.user.may, permission)
            if not has_permission():
                abort(403)
            return f(*args, **kw)
        return wrapped_f
    return wrap


class Permissions(object):
    """ Basic interface for user permissions and system policy.

    Note that you still need to allow some of the related actions, this
    just controls their behavior, not their activation.

    When sub classing this class, you must extend the class methods, not
    replace them, or you might break the ACLs in the wiki.
    Correct sub classing looks like this::

        def read(self, itemname):
            # Your special security rule
            if something:
                return False

            # Do not just return True or you break (ignore) ACLs!
            # This call will return correct permissions by checking ACLs:
            return Permissions.read(itemname)
    """
    def __init__(self, user):
        self.name = user.name

    def __getattr__(self, attr):
        """ Shortcut to handle all known ACL rights.

        if attr is a valid acl right, return a checking function for it.
        Else raise an AttributeError.

        :param attr: one of ACL rights as defined in acl_rights_(contents|functions)
        :rtype: function
        :returns: checking function for that right
        """
        if attr in app.cfg.acl_rights_contents:
            def may(itemname):
                backend = flaskg.storage._get_backend(itemname)[0]
                return backend._may(itemname, attr, username=self.name)
            return may
        if attr in app.cfg.acl_rights_functions:
            may = app.cfg.cache.acl_functions.may
            return lambda: may(self.name, attr)
        raise AttributeError(attr)


# make an alias for the default policy
Default = Permissions


class AccessControlList(object):
    """
    Access Control List - controls who may do what.

    Syntax of an ACL string:

        [+|-]User[,User,...]:[right[,right,...]] [[+|-]SomeGroup:...] ...
        ... [[+|-]Known:...] [[+|-]All:...]

        "User" is a user name and triggers only if the user matches.
        Any name can be used in acl lines, including names with spaces
        using exotic languages.

        "SomeGroup" is a group name. The group defines its members somehow,
        e.g. on a wiki page of this name as first level list with the group
        members' names.

        "Known" is a special group containing all valid / known users.

        "All" is a special group containing all users (Known and Anonymous users).

        "right" may be an arbitrary word like read, write or admin.
        Only valid words are accepted, others are ignored (see valid param).
        It is allowed to specify no rights, which means that no rights are given.

    How ACL is processed

        When some user is trying to access some ACL-protected resource,
        the ACLs will be processed in the order they are found. The first
        matching ACL will tell if the user has access to that resource
        or not.

        For example, the following ACL tells that SomeUser is able to
        read and write the resources protected by that ACL, while any
        member of SomeGroup (besides SomeUser, if part of that group)
        may also admin that, and every other user is able to read it.

            SomeUser:read,write SomeGroup:read,write,admin All:read

        In this example, SomeUser can read and write but can not admin
        items. Rights that are NOT specified on the right list are
        automatically set to NO.

    Using Prefixes

        To make the system more flexible, there are also two modifiers:
        the prefixes "+" and "-".

            +SomeUser:read -OtherUser:write

        The acl line above will grant SomeUser read right, and OtherUser
        write right, but will NOT block automatically all other rights
        for these users. For example, if SomeUser asks to write, the
        above acl line does not define if he can or can not write. He
        will be able to write if the acls checked before or afterwards
        allow this (see configuration options).

        Using prefixes, this acl line:

            SomeUser:read,write SomeGroup:read,write,admin All:read

        Can be written as:

            -SomeUser:admin SomeGroup:read,write,admin All:read

        Or even:

            +All:read -SomeUser:admin SomeGroup:read,write,admin

        Note that you probably would not want to use the second and
        third examples in ACL entries of some item. They are very
        useful in the wiki configuration though.
    """

    special_users = ["All", "Known", "Trusted"] # order is important

    def __init__(self, cfg, lines=[], default='', valid=None):
        """ Initialize an ACL, starting from <nothing>. """
        assert valid is not None
        self.acl_rights_valid = valid
        self.default = default
        self.auth_methods_trusted = cfg.auth_methods_trusted
        assert isinstance(lines, (list, tuple))
        if lines:
            self.acl = [] # [ ('User', {"read": 0, ...}), ... ]
            self.acl_lines = []
            for line in lines:
                self._addLine(line)
        else:
            self.acl = None
            self.acl_lines = None

    def has_acl(self):
        """ Checks whether we have a real acl here. """
        # self.acl == None means that there is NO acl.
        # self.acl == [] means that there is a empty acl.
        return self.acl is not None

    def _addLine(self, aclstring, remember=1):
        """ Add another ACL line

        This can be used in multiple subsequent calls to process longer lists.

        :param aclstring: acl string from item or configuration
        :param remember: should add the line to self.acl_lines
        """
        # Remember lines
        if remember:
            self.acl_lines.append(aclstring)

        # Iterate over entries and rights, parsed by acl string iterator
        acliter = ACLStringIterator(self.acl_rights_valid, aclstring)
        for modifier, entries, rights in acliter:
            if entries == ['Default']:
                self._addLine(self.default, remember=0)
            else:
                for entry in entries:
                    rightsdict = {}
                    if modifier:
                        # Only user rights are added to the right dict.
                        # + add right with value of 1
                        # - add right with value of 0
                        for right in rights:
                            rightsdict[right] = (modifier == '+')
                    else:
                        # All rights from acl_rights_valid are added to the
                        # dict, user rights with value of 1, and other with
                        # value of 0
                        for right in self.acl_rights_valid:
                            rightsdict[right] = (right in rights)
                    self.acl.append((entry, rightsdict))

    def may(self, name, dowhat):
        """ May <name> <dowhat>? Returns boolean answer.

            Note: this just checks THIS ACL, the before/default/after ACL must
                  be handled elsewhere, if needed.
        """
        groups = flaskg.groups
        allowed = None
        for entry, rightsdict in self.acl:
            if entry in self.special_users:
                handler = getattr(self, "_special_"+entry, None)
                allowed = handler(name, dowhat, rightsdict)
            elif entry in groups:
                if name in groups[entry]:
                    allowed = rightsdict.get(dowhat)
                else:
                    for special in self.special_users:
                        if special in entry:
                            handler = getattr(self, "_special_" + special, None)
                            allowed = handler(name, dowhat, rightsdict)
                            break # order of self.special_users is important
            elif entry == name:
                allowed = rightsdict.get(dowhat)
            if allowed is not None:
                return allowed
        return allowed # should be None

    def _special_All(self, name, dowhat, rightsdict):
        return rightsdict.get(dowhat)

    def _special_Known(self, name, dowhat, rightsdict):
        """ check if user <name> is known to us,
            that means that there is a valid user account present.
            works for subscription emails.
        """
        if user.getUserId(name): # is a user with this name known?
            return rightsdict.get(dowhat)
        return None

    def _special_Trusted(self, name, dowhat, rightsdict):
        """ check if user <name> is known AND has logged in using a trusted
            authentication method.
            Does not work for subsription emails that should be sent to <user>,
            as he is not logged in in that case.
        """
        if (flaskg.user.name == name and
            flaskg.user.auth_method in self.auth_methods_trusted):
            return rightsdict.get(dowhat)
        return None

    def __eq__(self, other):
        return self.acl_lines == other.acl_lines

    def __ne__(self, other):
        return self.acl_lines != other.acl_lines


class ContentACL(AccessControlList):
    """
    Content AccessControlList

    Uses cfg.acl_rights_contents if no list of valid rights is explicitly given.
    """
    def __init__(self, cfg, lines=[], default='', valid=None):
        if valid is None:
            valid = cfg.acl_rights_contents
        super(ContentACL, self).__init__(cfg, lines, default, valid)


class FunctionACL(AccessControlList):
    """
    Function AccessControlList

    Uses cfg.acl_rights_functions if no list of valid rights is explicitly given.
    """
    def __init__(self, cfg, lines=[], default='', valid=None):
        if valid is None:
            valid = cfg.acl_rights_functions
        super(FunctionACL, self).__init__(cfg, lines, default, valid)


class ACLStringIterator(object):
    """ Iterator for acl string

    Parse acl string and return the next entry on each call to next.
    Implements the Iterator protocol.

    Usage::

        iter = ACLStringIterator(rights_valid, 'user name:right')
        for modifier, entries, rights in iter:
            # process data
    """

    def __init__(self, rights, aclstring):
        """ Initialize acl iterator

        :param rights: the acl rights to consider when parsing
        :param aclstring: string to parse
        """
        self.rights = rights
        self.rest = aclstring.strip()
        self.finished = 0

    def __iter__(self):
        """ Required by the Iterator protocol """
        return self

    def next(self):
        """ Return the next values from the acl string

        When the iterator is finished and you try to call next, it
        raises a StopIteration. The iterator finishes as soon as the
        string is fully parsed or can not be parsed any more.

        :rtype: 3 tuple - (modifier, [entry, ...], [right, ...])
        :returns: values for one item in an acl string
        """
        # Handle finished state, required by iterator protocol
        if self.rest == '':
            self.finished = 1
        if self.finished:
            raise StopIteration

        # Get optional modifier [+|-]entries:rights
        modifier = ''
        if self.rest[0] in ('+', '-'):
            modifier, self.rest = self.rest[0], self.rest[1:]

        # Handle the Default meta acl
        if self.rest.startswith('Default ') or self.rest == 'Default':
            self.rest = self.rest[8:]
            entries, rights = ['Default'], []

        # Handle entries:rights pairs
        else:
            # Get entries
            try:
                entries, self.rest = self.rest.split(':', 1)
            except ValueError:
                self.finished = 1
                raise StopIteration("Can't parse rest of string")
            if entries == '':
                entries = []
            else:
                # TODO strip each entry from blanks?
                entries = entries.split(',')

            # Get rights
            try:
                rights, self.rest = self.rest.split(' ', 1)
                # Remove extra white space after rights fragment,
                # allowing using multiple spaces between items.
                self.rest = self.rest.lstrip()
            except ValueError:
                rights, self.rest = self.rest, ''
            rights = [r for r in rights.split(',') if r in self.rights]

        return modifier, entries, rights

