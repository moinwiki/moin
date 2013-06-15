# Copyright: 2011 MoinMoin:RonnyPfannschmidt
# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - storage subsystem
============================

We use a layered approach like this::

 Indexing Middleware               does complex stuff like indexing, searching,
 |                                 listing, lookup by name, ACL checks, ...
 v
 Routing  Middleware               dispatches to multiple backends based on the
 |                 |               namespace
 v                 v
 "stores" Backend  Other Backend   simple stuff: store, get, destroy revisions
 |           |
 v           v
 meta store  data store            simplest stuff: store, get, destroy and iterate
                                   over key/value pairs
"""


BACKENDS_PACKAGE = 'MoinMoin.storage.backends'

from MoinMoin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERPROFILES

BACKEND_DEFAULT, BACKEND_USERPROFILES = u'default', u'userprofiles'


def backend_from_uri(uri):
    """
    create a backend instance for uri
    """
    backend_name_uri = uri.split(':', 1)
    if len(backend_name_uri) != 2:
        raise ValueError("malformed backend uri: {0}".format(uri))
    backend_name, backend_uri = backend_name_uri
    module = __import__(BACKENDS_PACKAGE + '.' + backend_name, globals(), locals(), ['MutableBackend', ])
    return module.MutableBackend.from_uri(backend_uri)


def create_mapping(uri, namespaces, backends, acls):
    namespace_mapping = namespaces.items()
    acl_mapping = acls.items()
    backend_mapping = [
        (backend_name, backend_from_uri(uri % dict(backend=backend_name, kind="%(kind)s")))
        for backend_name in backends]
    # we need the longest mountpoints first, shortest last (-> '' is very last)
    namespace_mapping = sorted(namespace_mapping, key=lambda x: len(x[0]), reverse=True)
    acl_mapping = sorted(acl_mapping, key=lambda x: len(x[0]), reverse=True)
    return namespace_mapping, dict(backend_mapping), acl_mapping


def create_simple_mapping(uri='stores:fs:instance',
                          default_acl=None, userprofiles_acl=None):
    """
    When configuring storage, the admin needs to provide a namespace_mapping.
    To ease creation of such a mapping, this function provides sane defaults
    for different types of stores.
    The admin can just call this function, pass a hint on what type of stores
    he wants to use and a proper mapping is returned.

    :params uri: '<backend_name>:<backend_uri>' (general form)
                 backend_name must be a backend module name (e.g. stores)
                 the backend_uri must have a %(backend)s placeholder, it gets replaced
                 by the name of the backend (a simple, ascii string) and result
                 is given to to that backend's constructor

                 for the 'stores' backend, backend_uri looks like '<store_name>:<store_uri>'
                 store_name must be a store module name (e.g. fs)
                 the store_uri must have a %(kind)s placeholder, it gets replaced
                 by 'meta' or 'data' and the result is given to that store's constructor

                 e.g.:
                 'stores:fs:/path/to/store/%(backend)s/%(kind)s' will create a mapping
                 using the 'stores' backend with 'fs' stores and everything will be stored
                 to below /path/to/store/.
    """
    # if no acls are given, use something mostly harmless:
    if not default_acl:
        default_acl = dict(before=u'', default=u'All:read,write,create', after=u'', hierarchic=False)
    if not userprofiles_acl:
        userprofiles_acl = dict(before=u'All:', default=u'', after=u'', hierarchic=False)
    namespaces = {
        NAMESPACE_DEFAULT: BACKEND_DEFAULT,
        NAMESPACE_USERPROFILES + ':': BACKEND_USERPROFILES,
    }
    backends = {
        BACKEND_DEFAULT: None,
        BACKEND_USERPROFILES: None,
    }
    acls = {
        NAMESPACE_USERPROFILES + ':': userprofiles_acl,
        NAMESPACE_DEFAULT: default_acl,
    }
    return create_mapping(uri, namespaces, backends, acls)
