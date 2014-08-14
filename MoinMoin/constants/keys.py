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
CONTENTNGRAM = u"contentngram"

ACTION = u"action"
ADDRESS = u"address"
HOSTNAME = u"hostname"
USERID = u"userid"
MTIME = u"mtime"
EXTRA = u"extra"
COMMENT = u"comment"
SUMMARY = u"summary"
TRASH = u"trash"

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
IMMUTABLE_KEYS = [
    ACTION,
    ADDRESS,
    DATAID,
    EXTERNALLINKS,
    ITEMLINKS,
    ITEMTRANSCLUSIONS,
    MTIME,
    NAME_OLD,
    PARENTID,
    REVID,
    HASH_ALGORITHM,
    SIZE,
    USERID,
    WIKINAME,
]

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
SUBSCRIPTIONS = u"subscriptions"
SUBSCRIPTION_IDS = u"subscription_ids"
SUBSCRIPTION_PATTERNS = u"subscription_patterns"
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
NAMERE = u"namere"
NAMEPREFIX = u"nameprefix"

# in which backend is some revision stored?
BACKENDNAME = u"backendname"

USEROBJ_ATTRS = [
    # User objects proxy these attributes of the UserProfile objects:
    NAME, DISABLED, ITEMID, DISPLAY_NAME, ENC_PASSWORD, EMAIL, OPENID,
    MAILTO_AUTHOR, SHOW_COMMENTS, RESULTS_PER_PAGE, EDIT_ON_DOUBLECLICK, SCROLL_PAGE_AFTER_EDIT,
    EDIT_ROWS, THEME_NAME, LOCALE, TIMEZONE, SUBSCRIPTIONS, QUICKLINKS, CSS_URL,
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

# values for ACTION key
ACTION_SAVE = u"SAVE"
ACTION_REVERT = u"REVERT"
ACTION_TRASH = u"TRASH"
ACTION_COPY = u"COPY"
ACTION_RENAME = u"RENAME"

# defaul LOCALE key value
DEFAULT_LOCALE = u"en"

# key for composite name
FQNAME = u'fqname'
# Values that FIELD can take in the composite name: [NAMESPACE/][@FIELD/]NAME
FIELDS = [
    NAME_EXACT, ITEMID, REVID, TAGS, USERID, ITEMLINKS, ITEMTRANSCLUSIONS
]
# Fields that can be used as a unique identifier.
UFIELDS = [
    NAME_EXACT, ITEMID, REVID,
]
# Unique fields that are stored as list.
UFIELDS_TYPELIST = [NAME_EXACT, ]
