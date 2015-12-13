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

from whoosh.util.cache import lru_cache

from MoinMoin.constants.rights import (CREATE, READ, PUBREAD, WRITE, ADMIN, DESTROY, ACL_RIGHTS_CONTENTS)
from MoinMoin.constants.keys import ACL, ALL_REVS, LATEST_REVS, NAME_EXACT, ITEMID

from MoinMoin.security import AccessControlList

from MoinMoin.util.interwiki import split_fqname

from MoinMoin import log
logging = log.getLogger(__name__)


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
        :param user: a User instance (used for checking permissions)
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
        self.get_acls = lru_cache_decorator(self._get_acls)

    def _clear_acl_cache(self):
        # if we have modified the backend somehow so ACL lookup is influenced,
        # this functions need to get called, so it clears the ACL cache.
        # ACL lookups afterwards will fetch fresh info from the lower layers.
        self.get_acls.cache_clear()

    def _get_configured_acls(self, fqname):
        """
        for a fully-qualified itemname (namespace:name), get the acl configuration
        for that (part of the) namespace.

        :param fqname: fully qualified itemname
        :returns: acl configuration (acl dict from the acl_mapping)
        """
        itemname = fqname.value if fqname.field == NAME_EXACT else u''
        for prefix, acls in self.acl_mapping:
            if itemname.startswith(prefix):
                return acls
        else:
            raise ValueError('No acl_mapping entry found for item {0!r}'.format(fqname))

    def _get_acls(self, itemid=None, fqname=None):
        """
        return a list of (alternatively valid) effective acls for the item
        identified via itemid or fqname.
        this can be a list just containing the item's own acl (as only alternative),
        or a list with None, indicating no acl was found (in non-hierarchic mode).
        if hierarchic acl mode is enabled, a list of all valid parent acls will
        be returned.
        All lists are without considering before/default/after acls.
        """

        if itemid is not None:
            q = {ITEMID: itemid}
        elif fqname is not None:
            # itemid might be None for new, not yet stored items,
            # but we have fqname then
            q = fqname.query
        else:
            raise ValueError("need itemid or fqname")
        item = self.get_item(**q)
        acl = item.acl
        fqname = item.fqname
        if acl is not None:
            return [acl, ]
        acl_cfg = self._get_configured_acls(fqname)
        if acl_cfg['hierarchic']:
            # check parent(s), recursively
            parentids = item.parentids
            if parentids:
                acl_list = []
                for parentid in parentids:
                    pacls = self.get_acls(parentid, None)
                    acl_list.extend(pacls)
                return acl_list
        return [None, ]

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

    def may(self, fqname, capability, usernames=None):
        if usernames is not None and isinstance(usernames, (str, unicode)):
            # we got a single username (maybe str), make a list of unicode:
            if isinstance(usernames, str):
                usernames = usernames.decode('utf-8')
            usernames = [usernames, ]
        # TODO Make sure that fqname must be a CompositeName class instance, not unicode or list.
        fqname = fqname[0] if isinstance(fqname, list) else fqname
        if isinstance(fqname, unicode):
            fqname = split_fqname(fqname)
        item = self.get_item(**fqname.query)
        allowed = item.allows(capability, user_names=usernames)
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
    def fqname(self):
        return self.item.fqname

    @property
    def parentids(self):
        return self.item.parentids

    @property
    def parentnames(self):
        return self.item.parentnames

    @property
    def name(self):
        return self.item.name

    @property
    def fqname(self):
        return self.item.fqname

    @property
    def fqnames(self):
        return self.item.fqnames

    @property
    def acl(self):
        return self.item.acl

    def __nonzero__(self):
        return bool(self.item)

    def full_acls(self):
        """
        iterator over all alternatively possible full acls for this item,
        including before/default/after acl.
        """
        fqname = self.item.fqname
        itemid = self.item.itemid
        acl_cfg = self.protector._get_configured_acls(fqname)
        before_acl = acl_cfg['before']
        after_acl = acl_cfg['after']
        for item_acl in self.protector.get_acls(itemid, fqname):
            if item_acl is None:
                item_acl = acl_cfg['default']
            yield u' '.join([before_acl, item_acl, after_acl])

    def allows(self, right, user_names=None):
        """ Check if usernames may have <right> access on this item.

        :param right: the right to check
        :param user_names: user names to use for permissions check (default is to
                          use the user names doing the current request)
        :rtype: bool
        :returns: True if you have permission or False
        """
        if user_names is None:
            user_names = self.protector.user.name
        # must be a non-empty list of user names
        assert isinstance(user_names, list)
        assert user_names
        acl_cfg = self.protector._get_configured_acls(self.item.fqname)
        for user_name in user_names:
            for full_acl in self.full_acls():
                allowed = self.protector.eval_acl(full_acl, acl_cfg['default'], user_name, right)
                if allowed is True and pchecker(right, allowed, self.item):
                    return True
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

    def store_revision(self, meta, data, overwrite=False, return_rev=False, fqname=None, **kw):
        self.require(WRITE)
        if not self:
            self.require(CREATE)
        if overwrite:
            self.require(DESTROY)
        if meta.get(ACL) != self.acl:
            self.require(ADMIN)
        rev = self.item.store_revision(meta, data, overwrite=overwrite, return_rev=return_rev, fqname=fqname, **kw)
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
    def fqname(self):
        return self.rev.fqname

    @property
    def fqnames(self):
        return self.rev.fqnames

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
