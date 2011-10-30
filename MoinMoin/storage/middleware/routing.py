# Copyright: 2008-2011 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2009 MoinMoin:ChristopherDenter
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - routing middleware

Routes requests to different backends depending on the item name.

Just think of UNIX filesystems, fstab and mount.

This middleware lets you mount backends that store items belonging to some
specific part of the namespace. Routing middleware has same API as a backend.
"""


from __future__ import absolute_import, division

from MoinMoin.config import NAME

from MoinMoin.storage.backends import BackendBase, MutableBackendBase


class Backend(MutableBackendBase):
    """
    router, behaves readonly for readonly mounts
    """
    def __init__(self, mapping):
        """
        Initialize router backend.

        The mapping given must satisfy the following criteria:
            * Order matters.
            * Mountpoints are just item names, including the special '' (empty)
              root item name.
            * Trailing '/' of a mountpoint will be stripped.
            * There *must* be a backend with mountpoint '' at the very
              end of the mapping. That backend is then used as root, which means
              that all items that don't lie in the namespace of any other
              backend are stored there.

        :type mapping: list of tuples of mountpoint -> backend mappings
        :param mapping: [(mountpoint, backend), ...]
        """
        self.mapping = [(mountpoint.rstrip('/'), backend) for mountpoint, backend in mapping]

    def open(self):
        for mountpoint, backend in self.mapping:
            backend.open()

    def close(self):
        for mountpoint, backend in self.mapping:
            backend.close()

    def _get_backend(self, itemname):
        """
        For a given fully-qualified itemname (i.e. something like Company/Bosses/Mr_Joe)
        find the backend it belongs to (given by this instance's mapping), the local
        itemname inside that backend and the mountpoint of the backend.

        :param itemname: fully-qualified itemname
        :returns: tuple of (backend, local itemname, mountpoint)
        """
        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:], mountpoint
        raise AssertionError("No backend found for {0!r}. Available backends: {1!r}".format(itemname, self.mapping))

    def __iter__(self):
        # Note: yields <backend_mountpoint>/<backend_revid> as router revid, so that this
        #       can be given to get_revision and be routed to the right backend.
        for mountpoint, backend in self.mapping:
            for revid in backend:
                yield (mountpoint, revid)

    def retrieve(self, name, revid):
        backend, _, mountpoint = self._get_backend(name)
        meta, data = backend.retrieve(revid)
        if mountpoint:
            name = meta[NAME]
            if name:
                meta[NAME] = u'{0}/{1}'.format(mountpoint, meta[NAME])
            else:
                meta[NAME] = mountpoint # no trailing slash!
        return meta, data

    # writing part
    def create(self):
        for mountpoint, backend in self.mapping:
            if isinstance(backend, MutableBackendBase):
                backend.create()
            #XXX else: log info?

    def destroy(self):
        for mountpoint, backend in self.mapping:
            if isinstance(backend, MutableBackendBase):
                backend.destroy()
            #XXX else: log info?

    def store(self, meta, data):
        mountpoint_itemname = meta[NAME]
        backend, itemname, mountpoint = self._get_backend(mountpoint_itemname)
        if not isinstance(backend, MutableBackendBase):
            raise TypeError('backend {0!r} mounted at {1!r} is readonly'.format(backend, mountpoint))
        meta[NAME] = itemname
        revid = backend.store(meta, data)
        meta[NAME] = mountpoint_itemname # restore the original name
        return revid

    def remove(self, name, revid):
        backend, _, mountpoint = self._get_backend(name)
        if not isinstance(backend, MutableBackendBase):
            raise TypeError('backend {0!r} mounted at {1!r} is readonly'.format(backend, mountpoint))
        backend.remove(revid)

