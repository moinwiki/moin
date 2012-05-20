# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - meta data key / index field name related constants
"""

# metadata keys
NAME = "name"
NAME_OLD = "name_old"

# if an item is reverted, we store the revision number we used for reverting there:
REVERTED_TO = "reverted_to"

# some metadata key constants:
ACL = "acl"

# This says: I am a system item
IS_SYSITEM = "is_syspage"
# This says: original sysitem as contained in release: <release>
SYSITEM_VERSION = "syspage_version"

# keys for storing group and dict information
# group of user names, e.g. for ACLs:
USERGROUP = "usergroup"
# needs more precise name / use case:
SOMEDICT = "somedict"

CONTENTTYPE = "contenttype"
SIZE = "size"
LANGUAGE = "language"
EXTERNALLINKS = "externallinks"
ITEMLINKS = "itemlinks"
ITEMTRANSCLUSIONS = "itemtransclusions"
TAGS = "tags"

ACTION = "action"
ADDRESS = "address"
HOSTNAME = "hostname"
USERID = "userid"
MTIME = "mtime"
EXTRA = "extra"
COMMENT = "comment"
SUMMARY = "summary"

# we need a specific hash algorithm to store hashes of revision data into meta
# data. meta[HASH_ALGORITHM] = hash(rev_data, HASH_ALGORITHM)
# some backends may use this also for other purposes.
HASH_ALGORITHM = 'sha1'
HASH_LEN = 40 # length of hex str representation of hash value

# some field names for whoosh index schema / documents in index:
NAME_EXACT = "name_exact"
ITEMID = "itemid"
REVID = "revid"
PARENTID = "parentid"
DATAID = "dataid"
WIKINAME = "wikiname"
CONTENT = "content"

# magic REVID for current revision:
CURRENT = "current"

# stuff from user profiles / for whoosh index
EMAIL = "email"
OPENID = "openid"
ALIASNAME = "aliasname"
THEME_NAME = "theme_name"
LOCALE = "locale"
TIMEZONE = "timezone"
ENC_PASSWORD = "enc_password"
SUBSCRIBED_ITEMS = "subscribed_items"
BOOKMARKS = "bookmarks"
QUICKLINKS = "quicklinks"
SESSION_KEY = "session_key"
SESSION_TOKEN = "session_token"
RECOVERPASS_KEY = "recoverpass_key"
EDIT_ON_DOUBLECLICK = "edit_on_doubleclick"
SHOW_COMMENTS = "show_comments"
MAILTO_AUTHOR = "mailto_author"
RESULTS_PER_PAGE = "results_per_page"
DISABLED = "disabled"

# index names
LATEST_REVS = 'latest_revs'
ALL_REVS = 'all_revs'

