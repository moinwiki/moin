# Copyright: 2008-2010 MoinMoin:ThomasWaldmann
# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - routing backend

    You can use this backend to route requests to different backends
    depending on the item name. I.e., you can specify mountpoints and
    map them to different backends. E.g. you could route all your items
    to an FSBackend and only items below hg/<youritemnamehere> go into
    a MercurialBackend and similarly tmp/<youritemnamehere> is for
    temporary items in a MemoryBackend() that are discarded when the
    process terminates.
"""


import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.error import ConfigurationError
from MoinMoin.storage.error import AccessDeniedError

from MoinMoin.storage import Backend as BackendBase
from MoinMoin.storage import Item as ItemBase
from MoinMoin.storage import NewRevision as NewRevisionBase
from MoinMoin.storage import StoredRevision as StoredRevisionBase

from MoinMoin.storage.backends.indexing import IndexingBackendMixin, IndexingItemMixin, IndexingRevisionMixin

from MoinMoin.storage.serialization import SerializableRevisionMixin, SerializableItemMixin, SerializableBackendMixin


class BareRouterBackend(BackendBase):
    """
    Router Backend - routes requests to different backends depending
    on the item name.

    For method docstrings, please see the "Backend" base class.
    """
    def __init__(self, mapping, *args, **kw):
        """
        Initialize router backend.

        The mapping given must satisfy the following criteria:
            * Order matters.
            * Mountpoints are just item names, including the special '' (empty)
              root item name. A trailing '/' of a mountpoint will be ignored.
            * There *must* be a backend with mountpoint '' (or '/') at the very
              end of the mapping. That backend is then used as root, which means
              that all items that don't lie in the namespace of any other
              backend are stored there.

        :type mapping: list of tuples of mountpoint -> backend mappings
        :param mapping: [(mountpoint, backend), ...]
        """
        super(BareRouterBackend, self).__init__(*args, **kw)
        self.mapping = [(mountpoint.rstrip('/'), backend) for mountpoint, backend in mapping]

    def close(self):
        super(BareRouterBackend, self).close()
        for mountpoint, backend in self.mapping:
            backend.close()
        self.mapping = []

    def _get_backend(self, itemname):
        """
        For a given fully-qualified itemname (i.e. something like Company/Bosses/Mr_Joe)
        find the backend it belongs to (given by this instance's mapping), the local
        itemname inside that backend and the mountpoint of the backend.

        Note: Internally (i.e. in all Router* classes) we always use the normalized
              item name for consistency reasons.

        :type itemname: str
        :param itemname: fully-qualified itemname
        :returns: tuple of (backend, itemname, mountpoint)
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(itemname)))

        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:], mountpoint
        raise AssertionError("No backend found for %r. Available backends: %r" % (itemname, self.mapping))

    def get_backend(self, namespace):
        """
        Given a namespace, return the backend mounted there.

        :type namespace: basestring
        :param namespace: The namespace of which we look the backend up.
        """
        return self._get_backend(namespace)[0]

    def iter_items_noindex(self):
        """
        Iterate over all items.

        Must not use the index as this method is used to *build* the index.

        @see: Backend.iter_items_noindex.__doc__
        """
        for mountpoint, backend in self.mapping:
            for item in backend.iter_items_noindex():
                yield RouterItem(self, item.name, item, mountpoint)

    # TODO: implement a faster iteritems using the index
    iteritems = iter_items_noindex

    def has_item(self, itemname):
        """
        @see: Backend.has_item.__doc__
        """
        # While we could use the inherited, generic implementation
        # it is generally advised to override this method.
        # Thus, we pass the call down.
        logging.debug("has_item: %r" % itemname)
        backend, itemname, mountpoint = self._get_backend(itemname)
        return backend.has_item(itemname)

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        logging.debug("get_item: %r" % itemname)
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(self, itemname, backend.get_item(itemname), mountpoint)

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__
        """
        logging.debug("create_item: %r" % itemname)
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(self, itemname, backend.create_item(itemname), mountpoint)


class RouterBackend(SerializableBackendMixin, IndexingBackendMixin, BareRouterBackend):
    pass


class BareRouterItem(ItemBase):
    """
    Router Item - Wraps 'real' storage items to make them aware of their full name.

    Items stored in the backends managed by the RouterBackend do not know their full
    name since the backend they belong to is looked up from a list for a given
    mountpoint and only the itemname itself (without leading mountpoint) is given to
    the specific backend.
    This is done so as to allow mounting a given backend at a different mountpoint.
    The problem with that is, of course, that items do not know their full name if they
    are retrieved via the specific backends directly. Thus, it is neccessary to wrap the
    items returned from those specific backends in an instance of this RouterItem class.
    This makes sure that an item in a specific backend only knows its local name (as it
    should be; this allows mounting at a different place without renaming all items) but
    items that the RouterBackend creates or gets know their fully qualified name.

    In order to achieve this, we must mimic the Item interface here. In addition to that,
    a backend implementor may have decided to provide additional methods on his Item class.
    We can not know that here, ahead of time. We must redirect any attribute lookup to the
    encapsulated item, hence, and only intercept calls that are related to the item name.
    To do this, we store the wrapped item and redirect all calls via this classes __getattr__
    method. For this to work, RouterItem *must not* inherit from Item, because otherwise
    the attribute would be looked up on the abstract base class, which certainly is not what
    we want.
    Furthermore there's a problem with __getattr__ and new-style classes' special methods
    which can be looked up here:
    http://docs.python.org/reference/datamodel.html#special-method-lookup-for-new-style-classes
    """
    def __init__(self, backend, item_name, item, mountpoint, *args, **kw):
        """
        :type backend: Object adhering to the storage API.
        :param backend: The backend this item belongs to.
        :type itemname: basestring.
        :param itemname: The name of the item (not the FQIN).
        :type item: Object adhering to the storage item API.
        :param item: The item we want to wrap.
        :type mountpoint: basestring.
        :param mountpoint: The mountpoint where this item is located.
        """
        self._get_backend = backend._get_backend
        self._itemname = item_name
        self._item = item
        self._mountpoint = mountpoint
        super(BareRouterItem, self).__init__(backend, item_name, *args, **kw)

    def __getattr__(self, attr):
        """
        Redirect all attribute lookups to the item that is proxied by this instance.

        Note: __getattr__ only deals with stuff that is not found in instance,
              this class and base classes, so be careful!
        """
        return getattr(self._item, attr)

    @property
    def name(self):
        """
        :rtype: str
        :returns: the item's fully-qualified name
        """
        mountpoint = self._mountpoint
        if mountpoint:
            mountpoint += '/'
        return mountpoint + self._itemname

    def __setitem__(self, key, value):
        """
        @see: Item.__setitem__.__doc__
        """
        return self._item.__setitem__(key, value)

    def __delitem__(self, key):
        """
        @see: Item.__delitem__.__doc__
        """
        return self._item.__delitem__(key)

    def __getitem__(self, key):
        """
        @see: Item.__getitem__.__doc__
        """
        return self._item.__getitem__(key)

    def keys(self):
        return self._item.keys()

    def change_metadata(self):
        return self._item.change_metadata()

    def publish_metadata(self):
        return self._item.publish_metadata()

    def rollback(self):
        return self._item.rollback()

    def commit(self):
        return self._item.commit()

    def rename(self, newname):
        """
        For intra-backend renames, this is the same as the normal Item.rename
        method.
        For inter-backend renames, this *moves* the complete item over to the
        new backend, possibly with a new item name.
        In order to avoid content duplication, the old item is destroyed after
        having been copied (in inter-backend scenarios only, of course).

        @see: Item.rename.__doc__
        """
        old_name = self._item.name
        backend, itemname, mountpoint = self._get_backend(newname)
        if mountpoint != self._mountpoint:
            # Mountpoint changed! That means we have to copy the item over.
            converts, skips, fails = backend.copy_item(self._item, verbose=False, name=itemname)
            assert len(converts) == 1

            new_item = backend.get_item(itemname)
            old_item = self._item
            self._item = new_item
            self._mountpoint = mountpoint
            self._itemname = itemname
            # We destroy the old item in order not to duplicate data.
            # It may be the case that the item we want to destroy is ACL protected. In that case,
            # the destroy() below doesn't irreversibly kill the item because at this point it is already
            # guaranteed that it lives on at another place and we do not require 'destroy' hence.
            try:
                # Perhaps we don't deal with acl protected items anyway.
                old_item.destroy()
            except AccessDeniedError:
                # OK, we're indeed routing to an ACL protected backend. Use unprotected item.
                old_item._item.destroy()

        else:
            # Mountpoint didn't change
            self._item.rename(itemname)
            self._itemname = itemname

    def list_revisions(self):
        return self._item.list_revisions()

    def create_revision(self, revno):
        """
        In order to make item name lookups via revision.item.name work, we need
        to wrap the revision here.

        @see: Item.create_revision.__doc__
        """
        rev = self._item.create_revision(revno)
        return NewRouterRevision(self, revno, rev)

    def get_revision(self, revno):
        """
        In order to make item name lookups via revision.item.name work, we need
        to wrap the revision here.

        @see: Item.get_revision.__doc__
        """
        rev = self._item.get_revision(revno)
        return StoredRouterRevision(self, revno, rev)

    def destroy(self):
        """
        ATTENTION!
        This method performs an irreversible operation and deletes potentially important
        data. Use with great care.

        @see: Item.destroy.__doc__
        """
        return self._item.destroy()


class RouterItem(SerializableItemMixin, IndexingItemMixin, BareRouterItem):
    pass


class BareNewRouterRevision(NewRevisionBase):
    """
    """
    def __init__(self, item, revno, revision, *args, **kw):
        self._item = item
        self._revision = revision
        super(BareNewRouterRevision, self).__init__(item, revno, *args, **kw)

    def __getattr__(self, attr):
        """
        Redirect all attribute lookups to the revision that is proxied by this instance.

        Note: __getattr__ only deals with stuff that is not found in instance,
              this class and base classes, so be careful!
        """
        return getattr(self._revision, attr)

    @property
    def item(self):
        """
        Here we have to return the RouterItem, which in turn wraps the real item
        and provides it with its full name that we need for the rev.item.name lookup.

        @see: Revision.item.__doc__
        """
        assert isinstance(self._item, RouterItem)
        return self._item

    @property
    def revno(self):
        return self._revision.revno

    @property
    def timestamp(self):
        return self._revision.timestamp

    def __setitem__(self, key, value):
        """
        We only need to redirect this manually here because python doesn't do that
        in combination with __getattr__. See RouterBackend.__doc__ for an explanation.

        As this class wraps generic Revisions, this may very well result in an exception
        being raised if the wrapped revision is a StoredRevision.
        """
        return self._revision.__setitem__(key, value)

    def __delitem__(self, key):
        """
        @see: RouterRevision.__setitem__.__doc__
        """
        return self._revision.__delitem__(key)

    def __getitem__(self, key):
        """
        @see: RouterRevision.__setitem__.__doc__
        """
        return self._revision.__getitem__(key)

    def keys(self):
        return self._revision.keys()

    def read(self, chunksize=-1):
        return self._revision.read(chunksize)

    def seek(self, position, mode=0):
        return self._revision.seek(position, mode)

    def tell(self):
        return self._revision.tell()

    def write(self, data):
        self._revision.write(data)

    def destroy(self):
        return self._revision.destroy()


class NewRouterRevision(SerializableRevisionMixin, IndexingRevisionMixin, BareNewRouterRevision):
    pass

class BareStoredRouterRevision(StoredRevisionBase):
    """
    """
    def __init__(self, item, revno, revision, *args, **kw):
        self._item = item
        self._revision = revision
        super(BareStoredRouterRevision, self).__init__(item, revno, *args, **kw)

    def __getattr__(self, attr):
        """
        Redirect all attribute lookups to the revision that is proxied by this instance.

        Note: __getattr__ only deals with stuff that is not found in instance,
              this class and base classes, so be careful!
        """
        return getattr(self._revision, attr)

    @property
    def item(self):
        """
        Here we have to return the RouterItem, which in turn wraps the real item
        and provides it with its full name that we need for the rev.item.name lookup.

        @see: Revision.item.__doc__
        """
        assert isinstance(self._item, RouterItem)
        return self._item

    @property
    def revno(self):
        return self._revision.revno

    @property
    def timestamp(self):
        return self._revision.timestamp

    def __getitem__(self, key):
        return self._revision.__getitem__(key)

    def keys(self):
        return self._revision.keys()

    def read(self, chunksize=-1):
        return self._revision.read(chunksize)

    def seek(self, position, mode=0):
        return self._revision.seek(position, mode)

    def tell(self):
        return self._revision.tell()

    def destroy(self):
        return self._revision.destroy()


class StoredRouterRevision(SerializableRevisionMixin, IndexingRevisionMixin, BareStoredRouterRevision):
    pass

