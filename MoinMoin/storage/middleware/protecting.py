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

from whoosh.util import lru_cache

from MoinMoin.config import ACL, CREATE, READ, PUBREAD, WRITE, DESTROY, ADMIN, \
                            PTIME, ACL_RIGHTS_CONTENTS, \
                            ALL_REVS, LATEST_REVS
from MoinMoin.security import AccessControlList

# max sizes of some lru caches:
LOOKUP_CACHE = 100  # ACL lookup for some itemname
PARSE_CACHE = 100  # ACL string -> ACL object parsing
EVAL_CACHE = 500  # ACL evaluation for some username / capability


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
        # The ProtectingMiddleware exists just 1 request long, but might have
        # to parse and evaluate huge amounts of ACLs. We avoid doing same stuff
        # again and again by using some fresh lru caches for each PMW instance.
        lru_cache_decorator = lru_cache(PARSE_CACHE)
        self.parse_acl = lru_cache_decorator(self._parse_acl)
        lru_cache_decorator = lru_cache(EVAL_CACHE)
        self.eval_acl = lru_cache_decorator(self._eval_acl)
        lru_cache_decorator = lru_cache(LOOKUP_CACHE)
        self.get_acl = lru_cache_decorator(self._get_acl)

    def _clear_acl_cache(self):
        # if we have modified the backend somehow so ACL lookup is influenced,
        # this functions need to get called, so it clears the ACL cache.
        # ACL lookups afterwards will fetch fresh info from the lower layers.
        self.get_acl.cache_clear()

    def _get_configured_acls(self, itemname):
        """
        for a fully-qualified itemname (namespace:name), get the acl configuration
        for that (part of the) namespace.

        @param itemname: fully qualified itemname
        @returns: acl configuration (acl dict from the acl_mapping)
        """
        for prefix, acls in self.acl_mapping:
            if itemname.startswith(prefix):
                return acls
        else:
            raise ValueError('No acl_mapping entry found for item {0!r}'.format(itemname))

    def _get_acl(self, fqname):
        """
        return the effective item_acl for item fqname (= its own acl, or,
        if hierarchic acl mode is enabled, of some parent item) - without
        before/default/after acls. return None if no acl was found.
        """
        item = self[fqname]
        acl = item.acl
        if acl is not None:
            return acl
        acl_cfg = self._get_configured_acls(fqname)
        if acl_cfg['hierarchic']:
            # check parent(s), recursively
            parent_tail = fqname.rsplit('/', 1)
            if len(parent_tail) == 2:
                parent, _ = parent_tail
                acl = self.get_acl(parent)
                if acl is not None:
                    return acl

    def _parse_acl(self, acl, default=''):
        return AccessControlList([acl, ], default=default, valid=self.valid_rights)

    def _eval_acl(self, acl, default_acl, user_name, right):
        aclobj = self.parse_acl(acl, default_acl)
        return aclobj.may(user_name, right)

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
        if isinstance(itemname, list):
            # if we get a list of names, just use first one to fetch item
            itemname = itemname[0]
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

    @property
    def acl(self):
        return self.item.acl

    def __nonzero__(self):
        return bool(self.item)

    def full_acl(self):
        """
        return the full acl for this item, including before/default/after acl.
        """
        fqname = self.item.fqname
        acl_cfg = self.protector._get_configured_acls(fqname)
        before_acl = acl_cfg['before']
        item_acl = self.protector.get_acl(fqname)
        if item_acl is None:
            item_acl = acl_cfg['default']
        after_acl = acl_cfg['after']
        acl = u' '.join([before_acl, item_acl, after_acl])
        return acl

    def allows(self, right, user_name=None):
        """ Check if username may have <right> access on this item.

        :param right: the right to check
        :param user_name: user name to use for permissions check (default is to
                          use the user name doing the current request)
        :rtype: bool
        :returns: True if you have permission or False
        """
        if user_name is None:
            user_name = self.protector.user.name0

        acl_cfg = self.protector._get_configured_acls(self.item.fqname)
        full_acl = self.full_acl()

        allowed = self.protector.eval_acl(full_acl, acl_cfg['default'], user_name, right)
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

    def store_revision(self, meta, data, overwrite=False, return_rev=False, **kw):
        self.require(WRITE)
        if not self:
            self.require(CREATE)
        if overwrite:
            self.require(DESTROY)
        rev = self.item.store_revision(meta, data, overwrite=overwrite, return_rev=return_rev, **kw)
        self.protector._clear_acl_cache()
        if return_rev:
            return ProtectedRevision(self.protector, rev, p_item=self)

    def store_all_revisions(self, meta, data):
        self.require(DESTROY)
        self.item.store_all_revisions(meta, data)
        self.protector._clear_acl_cache()

    def destroy_revision(self, revid):
        self.require(DESTROY)
        self.item.destroy_revision(revid)
        self.protector._clear_acl_cache()

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
    def name(self):
        return self.rev.name

    @property
    def meta(self):
        self.require(READ, PUBREAD)
        return self.rev.meta

    @property
    def data(self):
        self.require(READ, PUBREAD)
        return self.rev.data

    def set_context(self, context):
        self.rev.set_context(context)

    def close(self):
        self.rev.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __cmp__(self, other):
        return cmp(self.meta, other.meta)
