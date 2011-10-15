# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - ACL related constants
"""

# ACL rights that are valid in moin2
SUPERUSER = 'superuser'
NOTEXTCHA = 'notextcha'
# rights that control access to specific functionality
ACL_RIGHTS_FUNCTIONS = [SUPERUSER, NOTEXTCHA, ]

ADMIN = 'admin'
READ = 'read'
WRITE = 'write'
CREATE = 'create'
DESTROY = 'destroy'
# rights that control access to operations on contents
ACL_RIGHTS_CONTENTS = [READ, WRITE, CREATE, ADMIN, DESTROY, ]

