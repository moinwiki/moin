# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - namespaces middleware

Routes requests to different backends depending on the namespace.
"""

from moin.constants.keys import NAME, BACKENDNAME, NAMESPACE

from moin.storage.backends import MutableBackendBase


class Backend(MutableBackendBase):
    """
    namespace dispatcher, behaves readonly for readonly mounts
    """

    def __init__(self, namespaces, backends):
        """
        Initialize.

        The namespace mapping given must satisfy the following criteria:
            * Order matters.
            * Namespaces are unicode strings like '' (default ns), 'userprofiles:'
              (used to store userprofiles) or 'files:' (could map to a fileserver
              backend). Can be also a hierarchic ns spec like 'foo:bar:'.
            * There *must* be a default namespace entry for '' at the end of
              the list.

        namespaces = [
            ('userprofiles:', 'user_be'),
            ('', 'default_be'), # default ('') must be last
        ]

        The backends mapping maps backend names to backend instances:

        backends = {
            'default_be': BackendInstance1,
            'user_be': BackendInstance2,
        }

        :type namespaces: list of tuples of namespace specifier -> backend names
        :param namespaces: [(namespace, backend_name), ...]
        :type backends: dict backend names -> backends
        :param backends: {backend_name: backend, ...}
        """
        self.namespaces = namespaces
        self.backends = backends
        for namespace, backend_name in namespaces:
            assert isinstance(namespace, str)
            assert backend_name in backends

    @classmethod
    def from_uri(cls, uri):
        """
        create an instance using the data given in uri
        """
        raise NotImplementedError

    def open(self):
        for backend in self.backends.values():
            backend.open()

    def close(self):
        for backend in self.backends.values():
            backend.close()

    def _get_backend(self, fq_names):
        """
        For a given fully-qualified itemname (i.e. something like ns:itemname)
        find the backend it belongs to, the itemname without namespace
        spec and the namespace of the backend.

        :param fq_names: fully-qualified itemnames
        :returns: tuple of (backend name, local item name, namespace)
        """
        fq_name = fq_names[0]
        for namespace, backend_name in self.namespaces:
            if fq_name.startswith(namespace):
                item_names = [_fq_name[len(namespace) :] for _fq_name in fq_names]
                return backend_name, item_names, namespace.rstrip(":")
        raise AssertionError(f"No backend found for {fq_name!r}. Namespaces: {self.namespaces!r}")

    def __iter__(self):
        # Note: yields enough information so we can retrieve the revision from
        #       the right backend later (this is more than just the revid).
        for backend_name, backend in self.backends.items():
            for revid in backend:  # TODO maybe directly yield the backend?
                yield (backend_name, revid)

    def retrieve(self, backend_name, revid):
        backend = self.backends[backend_name]
        meta, data = backend.retrieve(revid)
        return meta, data

    # writing part
    def create(self):
        for backend in self.backends.values():
            if isinstance(backend, MutableBackendBase):
                backend.create()

    def destroy(self):
        for backend in self.backends.values():
            if isinstance(backend, MutableBackendBase):
                backend.destroy()

    def store(self, meta, data):
        namespace = meta.get(NAMESPACE)
        if namespace is None:
            # if there is no NAMESPACE in metadata, we assume that the NAME
            # is fully qualified and determine the namespace from it:
            fq_names = meta[NAME]
            assert isinstance(fq_names, list)
            if fq_names:
                backend_name, item_names, namespace = self._get_backend(fq_names)
                # side effect: update the metadata with namespace and short item name (no ns)
                meta[NAMESPACE] = namespace
                meta[NAME] = item_names
            else:
                raise ValueError("can not determine namespace: empty NAME list, no NAMESPACE metadata present")
        else:
            if namespace:
                namespace += ":"  # needed for _get_backend
            backend_name, _, _ = self._get_backend([namespace])
        backend = self.backends[backend_name]

        if not isinstance(backend, MutableBackendBase):
            raise TypeError(f"backend {backend_name} is readonly!")

        revid = backend.store(meta, data)

        # add the BACKENDNAME after storing, so it gets only into
        # the index, but not in stored metadata:
        meta[BACKENDNAME] = backend_name
        return backend_name, revid

    def remove(self, backend_name, revid, destroy_data):
        backend = self.backends[backend_name]
        if not isinstance(backend, MutableBackendBase):
            raise TypeError(f"backend {backend_name} is readonly")
        backend.remove(revid, destroy_data)
