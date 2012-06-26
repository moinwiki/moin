# Copyright: 2007 MoinMoin:HeinrichWendel
# Copyright: 2008 MoinMoin:ChristopherDenter
# Copyright: 2009 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin storage errors
"""


from MoinMoin.error import CompositeError


class StorageError(CompositeError):
    """
    General class for exceptions on the storage layer.
    """

class BackendError(StorageError):
    """
    Raised if the backend couldn't commit the action.
    """

class NoSuchItemError(BackendError):
    """
    Raised if the requested item does not exist.
    """

class ItemAlreadyExistsError(BackendError):
    """
    Raised if the Item you are trying to create already exists.
    """

class NoSuchRevisionError(BackendError):
    """
    Raised if the requested revision of an item does not exist.
    """

class RevisionAlreadyExistsError(BackendError):
    """
    Raised if the Revision you are trying to create already exists.
    """
