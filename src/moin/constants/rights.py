# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - ACL related constants
"""

# ACL rights that are valid in moin2

# superuser enables access to some critical functionality,
# it is not related to CONTENT rights.
SUPERUSER = "superuser"

# rights that control access to specific functionality
ACL_RIGHTS_FUNCTIONS = [SUPERUSER]


# admin means to be able to change, add, remove ACLs (change meta[ACL])
ADMIN = "admin"

# read means to be able to read revision data, unconditionally
# TODO: define revision meta read behaviour
READ = "read"

# pubread means to be able to read revision data when published
PUBREAD = "pubread"

# write means to be able to change meta/data by creating a new revision,
# so the previous data is still there, unchanged.
WRITE = "write"

# create means to be able to create a new item (no older revisions, new ITEMID)
CREATE = "create"

# destroy means to be able to change or remove one or all existing revisions,
# this includes overwriting existing revision meta/data with new meta/data.
DESTROY = "destroy"

# rights that control access to operations on contents
ACL_RIGHTS_CONTENTS = [READ, PUBREAD, WRITE, CREATE, ADMIN, DESTROY]

# special user groups - order is important
SPECIAL_USERS = ["All", "Known", "Trusted"]
