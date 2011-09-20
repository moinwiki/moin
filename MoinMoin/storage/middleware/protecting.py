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

import logging

from config import ACL, CREATE, READ, WRITE, OVERWRITE, DESTROY, ADMIN


class AccessDenied(Exception):
    """
    raised when a user is denied access to an Item or Revision by ACL.
    """


class ProtectingMiddleware(object):
    def __init__(self, indexer, user_name):
        """
        :param indexer: indexing middleware instance
        :param user_name: the user's name (used for checking permissions)
        """
        self.indexer = indexer
        self.user_name = user_name

    def search(self, q, all_revs=False, **kw):
        for rev in self.indexer.search(q, all_revs, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ):
                yield rev

    def search_page(self, q, all_revs=False, pagenum=1, pagelen=10, **kw):
        for rev in self.indexer.search_page(q, all_revs, pagenum, pagelen, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ):
                yield rev

    def documents(self, all_revs=False, **kw):
        for rev in self.indexer.documents(all_revs, **kw):
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ):
                yield rev

    def document(self, all_revs=False, **kw):
        rev = self.indexer.document(all_revs, **kw)
        if rev:
            rev = ProtectedRevision(self, rev)
            if rev.allows(READ):
                return rev

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

    def __nonzero__(self):
        return bool(self.item)

    def allows(self, capability):
        """
        check latest ACL whether capability is allowed
        """
        # TODO: this is just a temporary hack to be able to test this without real ACL code,
        # replace it by a sane one later.
        # e.g. acl = "joe:read"  --> user joe may read
        acl = self.item.acl
        user_name = self.protector.user_name
        if acl is None or user_name is None:
            allow = True
        else:
            allow = "%s:%s" % (user_name, capability) in acl
        #print "item allows user '%s' to '%s' (acl: %s): %s" % (user_name, capability, acl, ["no", "yes"][allow])
        return allow

    def require(self, capability):
        if not self.allows(capability):
            raise AccessDenied("item does not allow user '%r' to '%r'" % (self.protector.user_name, capability))

    def iter_revs(self):
        self.require(READ)
        if self:
            for rev in self.item.iter_revs():
                yield ProtectedRevision(self.protector, rev, p_item=self)

    def __getitem__(self, revid):
        self.require(READ)
        rev = self.item[revid]
        return ProtectedRevision(self.protector, rev, p_item=self)

    def get_revision(self, revid):
        return self[revid]

    def store_revision(self, meta, data, overwrite=False):
        self.require(WRITE)
        if not self:
            self.require(CREATE)
        if overwrite:
            self.require(OVERWRITE)
        rev = self.item.store_revision(meta, data, overwrite=overwrite)
        return ProtectedRevision(self.protector, rev, p_item=self)

    def store_all_revisions(self, meta, data):
        self.require(OVERWRITE)
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

    def require(self, capability):
        if not self.allows(capability):
            raise AccessDenied("revision does not allow '%r'" % (capability, ))

    @property
    def revid(self):
        return self.rev.revid

    @property
    def meta(self):
        self.require(READ)
        return self.rev.meta

    @property
    def data(self):
        self.require(READ)
        return self.rev.data

    def close(self):
        self.rev.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __cmp__(self, other):
        return cmp(self.meta, other.meta)

