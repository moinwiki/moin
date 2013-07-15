# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - meta data key / index field name related constants
"""

# metadata keys
NAME = u"name"
NAME_OLD = u"name_old"
NAMESPACE = u"namespace"

# if an item is reverted, we store the revision number we used for reverting there:
REVERTED_TO = u"reverted_to"

# some metadata key constants:
ACL = u"acl"

# keys for storing group and dict information
# group of user names, e.g. for ACLs:
USERGROUP = u"usergroup"
# needs more precise name / use case:
SOMEDICT = u"somedict"

# TODO review plural constants
CONTENTTYPE = u"contenttype"
ITEMTYPE = u"itemtype"
SIZE = u"size"
LANGUAGE = u"language"
EXTERNALLINKS = u"externallinks"
ITEMLINKS = u"itemlinks"
ITEMTRANSCLUSIONS = u"itemtransclusions"
TAGS = u"tags"

ACTION = u"action"
ADDRESS = u"address"
HOSTNAME = u"hostname"
USERID = u"userid"
MTIME = u"mtime"
EXTRA = u"extra"
COMMENT = u"comment"
SUMMARY = u"summary"

# we need a specific hash algorithm to store hashes of revision data into meta
# data. meta[HASH_ALGORITHM] = hash(rev_data, HASH_ALGORITHM)
# some backends may use this also for other purposes.
HASH_ALGORITHM = u"sha1"
HASH_LEN = 40  # length of hex str representation of hash value

# some field names for whoosh index schema / documents in index:
NAME_EXACT = u"name_exact"
ITEMID = u"itemid"
REVID = u"revid"
PARENTID = u"parentid"
DATAID = u"dataid"
WIKINAME = u"wikiname"
CONTENT = u"content"

# magic REVID for current revision:
CURRENT = u"current"

# stuff from user profiles / for whoosh index
EMAIL = u"email"
OPENID = u"openid"
DISPLAY_NAME = u"display_name"
THEME_NAME = u"theme_name"
LOCALE = u"locale"
TIMEZONE = u"timezone"
ENC_PASSWORD = u"enc_password"
SUBSCRIBED_ITEMS = u"subscribed_items"
SUBSCRIPTION_IDS = u"subscription_ids"
BOOKMARKS = u"bookmarks"
QUICKLINKS = u"quicklinks"
SESSION_KEY = u"session_key"
SESSION_TOKEN = u"session_token"
RECOVERPASS_KEY = u"recoverpass_key"  # TODO: this is used for email confirmation as well, maybe it needs better name
EDIT_ON_DOUBLECLICK = u"edit_on_doubleclick"
SCROLL_PAGE_AFTER_EDIT = u"scroll_page_after_edit"
SHOW_COMMENTS = u"show_comments"
MAILTO_AUTHOR = u"mailto_author"
CSS_URL = u"css_url"
EDIT_ROWS = u"edit_rows"
RESULTS_PER_PAGE = u"results_per_page"
WANT_TRIVIAL = u"want_trivial"
EMAIL_SUBSCRIBED_EVENTS = u"email_subscribed_events"
DISABLED = u"disabled"
EMAIL_UNVALIDATED = u"email_unvalidated"

# in which backend is some revision stored?
BACKENDNAME = u"backendname"

USEROBJ_ATTRS = [
    # User objects proxy these attributes of the UserProfile objects:
    NAME, DISABLED, ITEMID, DISPLAY_NAME, ENC_PASSWORD, EMAIL, OPENID,
    MAILTO_AUTHOR, SHOW_COMMENTS, RESULTS_PER_PAGE, EDIT_ON_DOUBLECLICK, SCROLL_PAGE_AFTER_EDIT,
    EDIT_ROWS, THEME_NAME, LOCALE, TIMEZONE, SUBSCRIBED_ITEMS, SUBSCRIPTION_IDS,
    QUICKLINKS, CSS_URL,
]

# keys for blog homepages
LOGO = u"logo"
SUPERTAGS = u"supertags"
# keys for blog entries
PTIME = u"ptime"

# keys for tickets
EFFORT = u"effort"
DIFFICULTY = u"difficulty"
SEVERITY = u"severity"
PRIORITY = u"priority"
ASSIGNED_TO = u"assigned_to"
SUPERSEDED_BY = u"superseded_by"
DEPENDS_ON = u"depends_on"
CLOSED = u"closed"

# index names
LATEST_REVS = 'latest_revs'
ALL_REVS = 'all_revs'
