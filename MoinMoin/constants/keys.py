# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - meta data key / index field name related constants
"""

# IMPORTANT: until we require a python >= 2.6.5, we need to keep the keys as
#            str (not unicode), because of "Issue #4978: Passing keyword
#            arguments as unicode strings is now allowed." (from 2.6.5 chglog)

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
ITEMTYPE = "itemtype"
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
SCROLL_PAGE_AFTER_EDIT = "scroll_page_after_edit"
SHOW_COMMENTS = "show_comments"
MAILTO_AUTHOR = "mailto_author"
CSS_URL = "css_url"
EDIT_ROWS = "edit_rows"
RESULTS_PER_PAGE = "results_per_page"
DISABLED = "disabled"

USEROBJ_ATTRS = [
    # User objects proxy these attributes of the UserProfile objects:
    NAME, DISABLED, ITEMID, ALIASNAME, ENC_PASSWORD, EMAIL, OPENID,
    MAILTO_AUTHOR, SHOW_COMMENTS, RESULTS_PER_PAGE, EDIT_ON_DOUBLECLICK,
    EDIT_ROWS, THEME_NAME, LOCALE, TIMEZONE, SUBSCRIBED_ITEMS, QUICKLINKS,
    CSS_URL,
]

# keys for blog homepages
LOGO = "logo"
SUPERTAGS = "supertags"
# keys for blog entries
PTIME = "ptime"

# index names
LATEST_REVS = 'latest_revs'
ALL_REVS = 'all_revs'
