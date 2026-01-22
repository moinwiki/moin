# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.


class AccessDenied(Exception):
    """
    Raised when a user is denied access to an Item or Revision by ACL.
    """
