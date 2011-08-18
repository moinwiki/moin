# Copyright: 2003-2011 MoinMoin:ThomasWaldmann
# Copyright: 2000-2004 Juergen Hermann <jh@web.de>
# Copyright: 2003 Gustavo Niemeyer
# Copyright: 2005 Oliver Graf
# Copyright: 2007 Alexander Schremmer
# Copyright: 2009 Christopher Denter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - ACL Middleware

This backend is a middleware implementing access control using ACLs (access
control lists) and is referred to as AMW (ACL MiddleWare) hereafter.
It does not store any data, but uses a given backend for this.
This middleware is injected between the user of the storage API and the actual
backend used for storage. It is independent of the backend being used.
Instances of the AMW are bound to individual request objects. The user whose
permissions the AMW checks is hence obtained by a lookup on the request object.
The backend itself (and the objects it returns) need to be wrapped in order
to make sure that no object of the real backend is (directly or indirectly)
made accessible to the user of the API.
The real backend is still available as an attribute of the request and can
be used by conversion utilities or for similar tasks (flaskg.unprotected_storage).
Regular users of the storage API, such as the views that modify an item,
*MUST NOT*, in any way, use the real backend unless the author knows *exactly*
what he's doing (as this may introduce security bugs without the code actually
being broken).

The classes wrapped are:
    * AclWrapperBackend (wraps MoinMoin.storage.Backend)
    * AclWrapperItem (wraps MoinMoin.storage.Item)
    * AclWrapperRevision (wraps MoinMoin.storage.Revision)

When an attribute is 'wrapped' it means that, in this context, the user's
permissions are checked prior to attribute usage. If the user may not perform
the action he intended to perform, an AccessDeniedError is raised.
Otherwise the action is performed on the respective attribute of the real backend.
It is important to note here that the outcome of such an action may need to
be wrapped itself, as is the case when items or revisions are returned.

All wrapped classes must, of course, adhere to the normal storage API.
"""


from UserDict import DictMixin

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.security import AccessControlList

from MoinMoin.storage import Item, NewRevision, StoredRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError

from MoinMoin.config import ACL, ADMIN, READ, WRITE, CREATE, DESTROY


class AclWrapperBackend(object):
    """
    The AMW is bound to a specific request. The actual backend is retrieved
    from the config upon request initialization. Any method that is in some
    way relevant to security needs to be wrapped in order to ensure the user
    has the permissions necessary to perform the desired action.
    Note: This may *not* inherit from MoinMoin.storage.Backend because that would
    break our __getattr__ attribute 'redirects' (which are necessary because a backend
    implementor may decide to use his own helper functions which the items and revisions
    will still try to call).
    """
    def __init__(self, cfg, backend, hierarchic=False, before=u"", default=u"", after=u"", valid=None):
        """
        :type backend: Some object that implements the storage API.
        :param backend: The unprotected backend that we want to protect.
        :type hierarchic: bool
        :param hierarchic: Indicate whether we want to process ACLs in hierarchic mode.
        :type before: unicode
        :param before: ACL to be applied before all the other ACLs.
        :type default: unicode
        :param default: If no ACL information is given on the item in question, use this default.
        :type after: unicode
        :param after: ACL to be applied after all the other ACLs.
        :type valid: list of strings or None
        :param valid: If a list is given, only strings in the list are treated as valid acl privilege descriptors.
                      If None is give, the global wiki default is used.
        """
        self.cfg = cfg
        self.backend = backend
        self.hierarchic = hierarchic
        self.valid = valid if valid is not None else cfg.acl_rights_contents
        self.before = AccessControlList([before], default=default, valid=self.valid)
        self.default = AccessControlList([default], default=default, valid=self.valid)
        self.after = AccessControlList([after], default=default, valid=self.valid)

    def __getattr__(self, attr):
        # Attributes that this backend does not define itself are just looked
        # up on the real backend.
        return getattr(self.backend, attr)

    def search_items(self, searchterm):
        """
        @see: Backend.search_items.__doc__
        """
        for item in self.backend.search_items(searchterm):
            if self._may(item.name, READ):
                # The item returned needs to be wrapped because otherwise the
                # item's methods (like create_revision) wouldn't be wrapped.
                wrapped_item = AclWrapperItem(item, self)
                yield wrapped_item

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        if not self._may(itemname, READ):
            raise AccessDeniedError(flaskg.user.name, READ, itemname)
        real_item = self.backend.get_item(itemname)
        # Wrap the item here as well.
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def has_item(self, itemname):
        """
        @see: Backend.has_item.__doc__
        """
        # We do not hide the sheer existance of items. When trying
        # to create an item with the same name, the user would notice anyway.
        return self.backend.has_item(itemname)

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__
        """
        if not self._may(itemname, CREATE):
            raise AccessDeniedError(flaskg.user.name, CREATE, itemname)
        real_item = self.backend.create_item(itemname)
        # Wrap item.
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def iter_items_noindex(self):
        """
        @see: Backend.iter_items_noindex.__doc__
        """
        for item in self.backend.iteritems():
            if self._may(item.name, READ):
                yield AclWrapperItem(item, self)

    iteritems = iter_items_noindex

    def _get_acl(self, itemname):
        """
        Get ACL strings from the last revision's metadata and return ACL object.
        """
        try:
            item = self.backend.get_item(itemname)
            # we always use the ACLs set on the latest revision:
            current_rev = item.get_revision(-1)
            acl = current_rev[ACL]
            if not isinstance(acl, unicode):
                raise TypeError("%s metadata has unsupported type: %r" % (ACL, acl))
            acls = [acl, ]
        except (NoSuchItemError, NoSuchRevisionError, KeyError):
            # do not use default acl here
            acls = []
        default = self.default.default
        return AccessControlList(tuple(acls), default=default, valid=self.valid)

    def _may(self, itemname, right, username=None):
        """ Check if username may have <right> access on item <itemname>.

        For hierarchic=False we just check the item in question.

        For hierarchic=True, we check each item in the hierarchy. We
        start with the deepest item and recurse to the top of the tree.
        If one of those permits, True is returned.
        This is done *only* if there is *no ACL at all* (not even an empty one)
        on the items we 'recurse over'.

        For both configurations, we check `before` before the item/default
        acl and `after` after the item/default acl, of course.

        `default` is only used if there is no ACL on the item (and none on
        any of the item's parents when using hierarchic.)

        :param itemname: item to get permissions from
        :param right: the right to check
        :param username: username to use for permissions check (default is to
                         use the username doing the current request)
        :rtype: bool
        :returns: True if you have permission or False
        """
        if username is None:
            username = flaskg.user.name

        allowed = self.before.may(username, right)
        if allowed is not None:
            return allowed

        if self.hierarchic:
            items = itemname.split('/') # create item hierarchy list
            some_acl = False
            for i in range(len(items), 0, -1):
                # Create the next pagename in the hierarchy
                # starting at the leaf, going to the root
                name = '/'.join(items[:i])
                acl = self._get_acl(name)
                if acl.has_acl():
                    some_acl = True
                    allowed = acl.may(username, right)
                    if allowed is not None:
                        return allowed
                    # If the item has an acl (even one that doesn't match) we *do not*
                    # check the parents. We only check the parents if there's no acl on
                    # the item at all.
                    break
            if not some_acl:
                allowed = self.default.may(username, right)
                if allowed is not None:
                    return allowed
        else:
            acl = self._get_acl(itemname)
            if acl.has_acl():
                allowed = acl.may(username, right)
                if allowed is not None:
                    return allowed
            else:
                allowed = self.default.may(username, right)
                if allowed is not None:
                    return allowed

        allowed = self.after.may(username, right)
        if allowed is not None:
            return allowed

        return False


class AclWrapperItem(Item):
    """
    Similar to AclWrapperBackend. Wrap a storage item and protect its
    attributes by performing permission checks prior to performing the
    action and raising AccessDeniedErrors if appropriate.
    """
    def __init__(self, item, aclbackend):
        """
        :type item: Object adhering to the storage item API.
        :param item: The unprotected item we want to wrap.
        :type aclbackend: Instance of AclWrapperBackend.
        :param aclbackend: The AMW this item belongs to.
        """
        self._backend = aclbackend
        self._item = item
        self._may = aclbackend._may

    @property
    def name(self):
        """
        @see: Item.name.__doc__
        """
        return self._item.name

    # needed by storage.serialization:
    @property
    def element_name(self):
        return self._item.element_name
    @property
    def element_attrs(self):
        return self._item.element_attrs

    def require_privilege(*privileges):
        """
        This decorator is used in order to avoid code duplication
        when checking a user's permissions. It allows providing arguments
        that represent the permissions to check, such as READ and WRITE
        (see module level constants; don't pass strings, please).

        :type privileges: List of strings.
        :param privileges: Represent the privileges to check.
        """
        def wrap(f):
            def wrapped_f(self, *args, **kwargs):
                for privilege in privileges:
                    if not self._may(self.name, privilege):
                        username = flaskg.user.name
                        raise AccessDeniedError(username, privilege, self.name)
                return f(self, *args, **kwargs)
            return wrapped_f
        return wrap


    @require_privilege(WRITE)
    def __setitem__(self, key, value):
        """
        @see: Item.__setitem__.__doc__
        """
        return self._item.__setitem__(key, value)

    @require_privilege(WRITE)
    def __delitem__(self, key):
        """
        @see: Item.__delitem__.__doc__
        """
        return self._item.__delitem__(key)

    @require_privilege(READ)
    def __getitem__(self, key):
        """
        @see: Item.__getitem__.__doc__
        """
        return self._item.__getitem__(key)

    @require_privilege(READ)
    def keys(self):
        """
        @see: Item.keys.__doc__
        """
        return self._item.keys()

    @require_privilege(WRITE)
    def change_metadata(self):
        """
        @see: Item.change_metadata.__doc__
        """
        return self._item.change_metadata()

    @require_privilege(WRITE)
    def publish_metadata(self):
        """
        @see: Item.publish_metadata.__doc__
        """
        return self._item.publish_metadata()

    @require_privilege(READ)
    def get_revision(self, revno):
        """
        @see: Item.get_revision.__doc__
        """
        return AclWrapperRevision(self._item.get_revision(revno), self)

    @require_privilege(READ)
    def list_revisions(self):
        """
        @see: Item.list_revisions.__doc__
        """
        return self._item.list_revisions()

    @require_privilege(READ, WRITE)
    def rename(self, newname):
        """
        Rename item from name (src) to newname (dst).
        Note that there is no special rename privilege. By taking other
        privileges into account, we implicitly perform the permission check here.
        This checks R/W at src and W/C at dst. This combination was chosen for
        the following reasons:
         * It is the most intuitive of the possible solutions.
         * If we'd only check for R at src, everybody would be able to rename even
           ImmutablePages if there is a writable/creatable name somewhere else
           (e.g., Trash/).
         * 'delete' aka 'rename to trashbin' can be controlled with 'create':
           Just don't provide create for the trash namespace.
         * Someone without create in the target namespace cannot rename.

        @see: Item.rename.__doc__
        """
        # Special case since we need to check newname as well. Easier to special-case than
        # adjusting the decorator.
        username = flaskg.user.name
        if not self._may(newname, CREATE):
            raise AccessDeniedError(username, CREATE, newname)
        if not self._may(newname, WRITE):
            raise AccessDeniedError(username, WRITE, newname)
        return self._item.rename(newname)

    @require_privilege(WRITE)
    def commit(self):
        """
        @see: Item.commit.__doc__
        """
        return self._item.commit()

    # This does not require a privilege as the item must have been obtained
    # by either get_item or create_item already, which already check permissions.
    def rollback(self):
        """
        @see: Item.rollback.__doc__
        """
        return self._item.rollback()

    @require_privilege(DESTROY)
    def destroy(self):
        """
        USE WITH GREAT CARE!

        @see: Item.destroy.__doc__
        """
        return self._item.destroy()

    @require_privilege(WRITE)
    def create_revision(self, revno):
        """
        @see: Item.create_revision.__doc__
        """
        wrapped_revision = AclWrapperRevision(self._item.create_revision(revno), self)
        return wrapped_revision


class AclWrapperRevision(object, DictMixin):
    """
    Wrapper for revision classes. We need to wrap NewRevisions because they allow altering data.
    We need to wrap StoredRevisions since they offer a destroy() method and access to their item.
    The caller should know what kind of revision he gets. Hence, we just implement the methods of
    both, StoredRevision and NewRevision. If a method is invoked that is not defined on the
    kind of revision we wrap, we will see an AttributeError one level deeper anyway, so this is ok.
    """
    def __init__(self, revision, item):
        """
        :type revision: Object adhering to the storage revision API.
        :param revision: The revision we want to protect.
        :type item: Object adhering to the storage item API.
        :param item: The item this revision belongs to
        """
        self._revision = revision
        self._item = item
        self._may = item._may

    def __getattr__(self, attr):
        # Pass through any call that is not subject to ACL protection (e.g. serialize)
        return getattr(self._revision, attr)

    @property
    def item(self):
        """
        @see: Revision.item.__doc__
        """
        return self._item

    @property
    def timestamp(self):
        """This property accesses the creation timestamp of the revision"""
        return self._revision.timestamp

    def __setitem__(self, key, value):
        """
        In order to change an ACL on an item you must have the ADMIN privilege.
        We must allow the (unchanged) preceeding revision's ACL being stored
        into the new revision, though.

        TODO: the ACL specialcasing done here (requiring admin privilege for
              changing ACLs) is only one case of a more generic problem:
              Access (read,write,change) to some metadata must be checked.
              ACL - changing needs ADMIN priviledge
              userid, ip, hostname, etc. - writing them should be from system only
              content hash - writing it should be from system only
              For the metadata editing offered to the wiki user on the UI,
              we should only offer metadata for which the wiki user has change
              permissions. On save, we have to check the permissions.
              Idea: have metadata key prefixes, classifying metadata entries:
              security.* - security related
                      .acl - content acl
                      .insecure - allow insecure rendering (e.g. raw html)
              system.* - internal stuff, only system may process this
              user.* - user defined entries
              (... needs more thinking ...)

        @see: NewRevision.__setitem__.__doc__
        """
        if key == ACL:
            try:
                # This rev is not yet committed
                last_rev = self._item.get_revision(-1)
                last_acl = last_rev[ACL]
            except (NoSuchRevisionError, KeyError):
                last_acl = u''

            acl_changed = value != last_acl

            if acl_changed and not self._may(self._item.name, ADMIN):
                username = flaskg.user.name
                raise AccessDeniedError(username, ADMIN, self._item.name)
        return self._revision.__setitem__(key, value)

    def __getitem__(self, key):
        """
        @see: NewRevision.__getitem__.__doc__
        """
        return self._revision[key]

    def __delitem__(self, key):
        """
        @see: NewRevision.__delitem__.__doc__
        """
        del self._revision[key]

    def read(self, chunksize=-1):
        """
        @see: Backend._read_revision_data.__doc__
        """
        return self._revision.read(chunksize)

    def seek(self, position, mode=0):
        """
        @see: StringIO.StringIO().seek.__doc__
        """
        return self._revision.seek(position, mode)

    def destroy(self):
        """
        @see: Backend._destroy_revision.__doc__
        """
        if not self._may(self._item.name, DESTROY):
            username = flaskg.user.name
            raise AccessDeniedError(username, DESTROY + " revisions of", self._item.name)
        return self._revision.destroy()

    def write(self, data):
        """
        @see: Backend._write_revision_data.__doc__
        """
        return self._revision.write(data)

