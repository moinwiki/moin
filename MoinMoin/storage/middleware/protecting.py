# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - protecting middleware

This checks ACLs (access control lists), so a user will not be able to do
operations without the respective permissions.

Note: for method / attribute docs, please see the same methods / attributes in
      IndexingMiddleware class.
"""


from __future__ import absolute_import, division

import time

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.config import ACL, CREATE, READ, PUBREAD, WRITE, DESTROY, ADMIN, \
                            PTIME, ACL_RIGHTS_CONTENTS, \
                            ALL_REVS, LATEST_REVS
from MoinMoin.security import AccessControlList


class AccessDenied(Exception):
    """
    raised when a user is denied access to an Item or Revision by ACL.
    """


def pchecker(right, allowed, item):
    """some permissions need additional checking"""
    if allowed and right == PUBREAD:
        # PUBREAD permission is only granted after publication time (ptime)
        # if PTIME is not defined, we use MTIME (which is usually in the past)
        # if MTIME is not defined, we use now.
        # TODO: implement sth like PSTARTTIME <= now <= PENDTIME ?
        now = time.time()
        ptime = item.ptime or item.mtime or now
        allowed = now >= ptime
    return allowed


class ProtectingMiddleware(object):
    def __init__(self, indexer, user, acl_mapping):
        """
        :param indexer: indexing middleware instance
        :param user_name: the user's name (used for checking permissions)
        :param acl_mapping: list of (name_prefix, acls) tuples, longest prefix first, '' last
                            acls = dict with before, default, after, hierarchic entries
        """
        self.indexer = indexer
        self.user = user
        self.acl_mapping = acl_mapping
        self.valid_rights = ACL_RIGHTS_CONTENTS

    def get_acls(self, itemname):
        for prefix, acls in self.acl_mapping:
            if itemname.startswith(prefix):
                return acls
        else:
            raise ValueError('No acl_mapping entry found for item {0!r}'.format(itemname))

    def query_parser(self, default_fields, idx_name=LATEST_REVS):
        return self.indexer.query_parser(default_fields, idx_name=idx_name)

    def search(self, q, idx_name=LATEST_REVS, **kw):
        for rev in self.indexer.search(q, idx_name, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ) or rev.allows(PUBREAD):
                yield rev

    def search_page(self, q, idx_name=LATEST_REVS, pagenum=1, pagelen=10, **kw):
        for rev in self.indexer.search_page(q, idx_name, pagenum, pagelen, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ) or rev.allows(PUBREAD):
                yield rev

    def documents(self, idx_name=LATEST_REVS, **kw):
        for rev in self.indexer.documents(idx_name, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ) or rev.allows(PUBREAD):
                yield rev

    def document(self, idx_name=LATEST_REVS, **kw):
        rev = self.indexer.document(idx_name, **kw)
        if rev:
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ) or rev.allows(PUBREAD):
                return rev

    def has_item(self, name):
        return self.indexer.has_item(name)

    def __getitem__(self, name):
        item = self.indexer[name]
        return ProtectedItem(self, item)

    def get_item(self, **query):
        item = self.indexer.get_item(**query)
        return ProtectedItem(self, item)

    def create_item(self, **query):
        item = self.indexer.create_item(**query)
        return ProtectedItem(self, item)

    def existing_item(self, **query):
        item = self.indexer.existing_item(**query)
        return ProtectedItem(self, item)

    def may(self, itemname, capability, username=None):
        item = self[itemname]
        allowed = item.allows(capability, user_name=username)
        return allowed


class ProtectedItem(object):
    def __init__(self, protector, item):
        """
        :param protector: protector middleware
        :param item: item to protect
        """
        self.protector = protector
        self.item = item

    @property
    def itemid(self):
        return self.item.itemid

    @property
    def name(self):
        return self.item.name

    def __nonzero__(self):
        return bool(self.item)

    def _allows(self, right, user_name):
        """
        check permissions in this item without considering before/after acls
        """
        acls = self.protector.get_acls(self.item.name)
        acl = self.item.acl
        if acl is not None:
            # If the item has an acl (even one that doesn't match) we *do not*
            # check the parents. We only check the parents if there's no acl on
            # the item at all.
            acl = AccessControlList([acl, ], acls['default'], valid=self.protector.valid_rights)
            allowed = acl.may(user_name, right)
            if allowed is not None:
                return pchecker(right, allowed, self.item)
        else:
            if acls['hierarchic']:
                # check parent(s), recursively
                parent_tail = self.item.name.rsplit('/', 1)
                if len(parent_tail) == 2:
                    parent, _ = parent_tail
                    parent_item = self.protector[parent]
                    allowed = parent_item._allows(right, user_name)
                    if allowed is not None:
                        return pchecker(right, allowed, self.item)

            acl = AccessControlList([acls['default'], ], valid=self.protector.valid_rights)
            allowed = acl.may(user_name, right)
            if allowed is not None:
                return pchecker(right, allowed, self.item)

    def allows(self, right, user_name=None):
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
        if user_name is None:
            user_name = self.protector.user.name

        acls = self.protector.get_acls(self.item.name)

        before = AccessControlList([acls['before'], ], valid=self.protector.valid_rights)
        allowed = before.may(user_name, right)
        if allowed is not None:
            return pchecker(right, allowed, self.item)

        allowed = self._allows(right, user_name)
        if allowed is not None:
            return pchecker(right, allowed, self.item)

        after = AccessControlList([acls['after'], ], valid=self.protector.valid_rights)
        allowed = after.may(user_name, right)
        if allowed is not None:
            return pchecker(right, allowed, self.item)

        return False

    def require(self, *capabilities):
        """require that at least one of the capabilities is allowed"""
        if not any(self.allows(c) for c in capabilities):
            capability = " or ".join(capabilities)
            raise AccessDenied("item does not allow user '{0!r}' to '{1!r}' [{2!r}]".format(
                               self.protector.user.name, capability, self.item.acl))

    def iter_revs(self):
        self.require(READ)
        if self:
            for rev in self.item.iter_revs():
                yield ProtectedRevision(self.protector, rev, p_item=self)

    def __getitem__(self, revid):
        self.require(READ, PUBREAD)
        rev = self.item[revid]
        return ProtectedRevision(self.protector, rev, p_item=self)

    def get_revision(self, revid):
        return self[revid]

    def store_revision(self, meta, data, overwrite=False, **kw):
        self.require(WRITE)
        if not self:
            self.require(CREATE)
        if overwrite:
            self.require(DESTROY)
        rev = self.item.store_revision(meta, data, overwrite=overwrite, **kw)
        return ProtectedRevision(self.protector, rev, p_item=self)

    def store_all_revisions(self, meta, data):
        self.require(DESTROY)
        self.item.store_all_revisions(meta, data)

    def destroy_revision(self, revid):
        self.require(DESTROY)
        self.item.destroy_revision(revid)

    def destroy_all_revisions(self):
        for rev in self.item.iter_revs():
            self.destroy_revision(rev.revid)


class ProtectedRevision(object):
    def __init__(self, protector, rev, p_item=None):
        """
        :param protector: Protector middleware
        :param rev: Revision to protect
        :param p_item: instance of ProtectedItem for rev.item (optional)
        """
        self.protector = protector
        self.rev = rev
        self.item = p_item or ProtectedItem(protector, rev.item)

    def allows(self, capability):
        # to check allowance for a revision, we always ask the item
        return self.item.allows(capability)

    def require(self, *capabilities):
        """require that at least one of the capabilities is allowed"""
        if not any(self.allows(c) for c in capabilities):
            capability = " or ".join(capabilities)
            raise AccessDenied("revision does not allow user '{0!r}' to '{1!r}' [{2!r}]".format(
                               self.protector.user.name, capability, self.item.item.acl))

    @property
    def revid(self):
        return self.rev.revid

    @property
    def meta(self):
        self.require(READ, PUBREAD)
        return self.rev.meta

    @property
    def data(self):
        self.require(READ, PUBREAD)
        return self.rev.data

    def close(self):
        self.rev.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __cmp__(self, other):
        return cmp(self.meta, other.meta)
