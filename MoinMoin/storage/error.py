"""
    MoinMoin storage errors

    @copyright: 2007 MoinMoin:HeinrichWendel,
                2008 MoinMoin:ChristopherDenter,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

from MoinMoin.i18n import _, L_, N_
from MoinMoin.error import CompositeError


class StorageError(CompositeError):
    """
    General class for exceptions on the storage layer.
    """
    pass

class AccessError(StorageError):
    """
    Raised if the action could not be commited because of access problems.
    """
    pass

class CouldNotDestroyError(AccessError):
    """
    Raised if the item/revision in question could not be destroyed due to
    an internal backend problem. NOT raised if the user does not have the
    'destroy' privilege. This exception describes a technical deletion
    problem, not missing ACLs.
    """
    pass

class AccessDeniedError(AccessError):
    """
    Raised if the required rights are not available to perform the action.
    """
    def __init__(self, username=None, priv=None, item=None):
        if None in (username, priv, item):
            message = _("Permission denied!")
        else:
            username = username or L_("You")
            message = _("%(username)s may not %(priv)s '%(item)s'.",
                        username=username, priv=_(priv), item=item)
            # XXX add _('...') for all privs elsewhere for extraction

        AccessError.__init__(self, message)

class LockingError(AccessError):
    """
    Raised if the action could not be commited because the Item is locked
    or the if the item could not be locked.
    """
    pass

class BackendError(StorageError):
    """
    Raised if the backend couldn't commit the action.
    """
    pass

class NoSuchItemError(BackendError):
    """
    Raised if the requested item does not exist.
    """
    pass

class ItemAlreadyExistsError(BackendError):
    """
    Raised if the Item you are trying to create already exists.
    """
    pass

class NoSuchRevisionError(BackendError):
    """
    Raised if the requested revision of an item does not exist.
    """
    pass

class RevisionAlreadyExistsError(BackendError):
    """
    Raised if the Revision you are trying to create already exists.
    """
    pass

class RevisionNumberMismatchError(BackendError):
    """
    Raised if a revision number that is not greater than the most recent revision
    number was passed or if the backend does not yet support non-contiguous or
    non-zero-based revision numbers and the operation violated these
    requirements.
    """
    pass

