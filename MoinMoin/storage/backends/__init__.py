# Copyright: 2007 MoinMoin:HeinrichWendel
# Copyright: 2008 MoinMoin:PawelPacana
# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2009-2010 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.
"""


from flask import g as flaskg

from MoinMoin.storage.serialization import unserialize
from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError
from MoinMoin.error import ConfigurationError
from MoinMoin.storage.backends import router, fs, fs2, fs19, memory

CONTENT = 'content'
USERPROFILES = 'userprofiles'
TRASH = 'trash'

FS19_PREFIX = "fs19:"
FS_PREFIX = "fs:"
FS2_PREFIX = "fs2:"
HG_PREFIX = "hg:"
SQLA_PREFIX = "sqla:"
MEMORY_PREFIX = "memory:"


def create_simple_mapping(backend_uri='fs:instance', content_acl=None, user_profile_acl=None):
    """
    When configuring storage, the admin needs to provide a namespace_mapping.
    To ease creation of such a mapping, this function provides sane defaults
    for different types of backends.
    The admin can just call this function, pass a hint on what type of backend
    he wants to use and a proper mapping is returned.
    If the user did not specify anything, we use three FSBackends with user/,
    data/ and trash/ directories by default.
    """
    # XXX How to properly get these values from the users config?
    ns_content = u'/'
    ns_user_profile = u'UserProfile/'
    ns_trash = u'Trash/'

    if not content_acl:
        content_acl = dict(
            before=u'',
            default=u'All:read,write,create', # mostly harmless by default
            after=u'',
            hierarchic=False,
        )

    if not user_profile_acl:
        user_profile_acl = dict(
            before=u'All:', # harmless by default
            default=u'',
            after=u'',
            hierarchic=False,
        )

    def _create_backends(BackendClass, backend_uri):
        backends = []
        for name in [CONTENT, USERPROFILES, TRASH, ]:
            parms = dict(nsname=name)
            backend = BackendClass(backend_uri % parms)
            backends.append(backend)
        return backends

    if backend_uri.startswith(FS_PREFIX):
        instance_uri = backend_uri[len(FS_PREFIX):]
        content, userprofile, trash = _create_backends(fs.FSBackend, instance_uri)

    elif backend_uri.startswith(FS2_PREFIX):
        instance_uri = backend_uri[len(FS2_PREFIX):]
        content, userprofile, trash = _create_backends(fs2.FS2Backend, instance_uri)

    elif backend_uri.startswith(HG_PREFIX):
        # Due to external dependency that may not always be present, import hg backend here:
        from MoinMoin.storage.backends import hg
        instance_uri = backend_uri[len(HG_PREFIX):]
        content, userprofile, trash = _create_backends(hg.MercurialBackend, instance_uri)

    elif backend_uri.startswith(SQLA_PREFIX):
        # XXX Move this import to the module level if we depend on sqlalchemy and it is in sys.path
        from MoinMoin.storage.backends import sqla
        instance_uri = backend_uri[len(SQLA_PREFIX):]
        content, userprofile, trash = _create_backends(sqla.SQLAlchemyBackend, instance_uri)

    elif backend_uri == MEMORY_PREFIX:
        instance_uri = ''
        content, userprofile, trash = _create_backends(memory.MemoryBackend, instance_uri)

    elif backend_uri.startswith(FS19_PREFIX):
        # special case: old moin19 stuff
        from os import path
        data_dir = backend_uri[len(FS19_PREFIX):]
        userprofile = fs19.FSUserBackend(path.join(data_dir, 'user'), '/dev/shm') # assumes user below data_dir
        content = fs19.FSPageBackend(data_dir, '/dev/shm', deleted_mode='keep', default_markup=u'wiki')
        namespace_mapping = [
                        # no trash
                        (ns_user_profile, userprofile, user_profile_acl),
                        (ns_content, content, content_acl),
        ]
        return namespace_mapping, 'sqlite://'

    else:
        raise ConfigurationError("No proper backend uri provided. Given: %r" % backend_uri)

    namespace_mapping = [
                    (ns_trash, trash, content_acl),
                    (ns_user_profile, userprofile, user_profile_acl),
                    (ns_content, content, content_acl),
    ]

    return namespace_mapping


def upgrade_sysitems(xmlfile):
    """
    Upgrade the wiki's system pages from an XML file.
    """
    tmp_backend = router.RouterBackend([('/', memory.MemoryBackend())])
    unserialize(tmp_backend, xmlfile)

    # clone to real backend from config WITHOUT checking ACLs!
    flaskg.unprotected_storage.clone(tmp_backend)

