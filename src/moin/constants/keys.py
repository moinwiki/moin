# Copyright: 2011 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - meta data key / index field name related constants
"""

# metadata keys
NAME = "name"  # a list of strings, not useful for searching nor sorting, see #364
NAMES = "names"  # fullnames of item separated by |, useful for indexing/searching/display
NAME_SORT = "name_sort"  # useful for sorting, slashes removed because of whoosh, see #209
NAME_OLD = "name_old"
NAMESPACE = "namespace"

# if an item is reverted, we store the revision number we used for reverting there:
REVERTED_TO = "reverted_to"

# some metadata key constants:
ACL = "acl"

# keys for storing group and dict information
# group of user names, e.g. for ACLs:
USERGROUP = "usergroup"
WIKIDICT = "wikidict"

# TODO review plural constants
CONTENTTYPE = "contenttype"
ITEMTYPE = "itemtype"
SIZE = "size"
LANGUAGE = "language"
EXTERNALLINKS = "externallinks"
ITEMLINKS = "itemlinks"
ITEMTRANSCLUSIONS = "itemtransclusions"
TAGS = "tags"
HAS_TAG = "has_tag"
TEMPLATE = "template"  # a TAGS value identifying an item as a template
CONTENTNGRAM = "contentngram"
SUMMARYNGRAM = "summaryngram"
NAMENGRAM = "namengram"

ACTION = "action"
ADDRESS = "address"
HOSTNAME = "hostname"
USERID = "userid"
MTIME = "mtime"
EXTRA = "extra"
COMMENT = "comment"
SUMMARY = "summary"
TRASH = "trash"

# we need a specific hash algorithm to store hashes of revision data into meta
# data. meta[HASH_ALGORITHM] = hash(rev_data, HASH_ALGORITHM)
# some backends may use this also for other purposes.
HASH_ALGORITHM = "sha1"
HASH_LEN = 40  # length of hex str representation of hash value

# some field names for whoosh index schema / documents in index:
NAME_EXACT = "name_exact"
ITEMID = "itemid"
REVID = "revid"
REV_NUMBER = "rev_number"
PARENTID = "parentid"
PARENTNAMES = "parentnames"
DATAID = "dataid"
WIKINAME = "wikiname"
CONTENT = "content"
REFERS_TO = "refers_to"
# list of metadata fields that editors cannot modify
# excludes COMMENT, SUMMARY, TAG, USERGROUP and WIKIDICT
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
    REFERS_TO,
    REVID,
    HASH_ALGORITHM,
    SIZE,
    USERID,
    WIKINAME,
    CONTENTTYPE,
    ITEMID,
    ITEMTYPE,
    NAMESPACE,
    REV_NUMBER,
]

# magic REVID for current revision:
CURRENT = "current"

# stuff from user profiles / for whoosh index
EMAIL = "email"
DISPLAY_NAME = "display_name"
THEME_NAME = "theme_name"
LOCALE = "locale"
TIMEZONE = "timezone"
ENC_PASSWORD = "enc_password"
SUBSCRIPTIONS = "subscriptions"
SUBSCRIPTION_IDS = "subscription_ids"
SUBSCRIPTION_PATTERNS = "subscription_patterns"
BOOKMARKS = "bookmarks"
QUICKLINKS = "quicklinks"
SESSION_KEY = "session_key"
SESSION_TOKEN = "session_token"
RECOVERPASS_KEY = "recoverpass_key"  # TODO: this is used for email confirmation as well, maybe it needs better name
EDIT_ON_DOUBLECLICK = "edit_on_doubleclick"
SCROLL_PAGE_AFTER_EDIT = "scroll_page_after_edit"
SHOW_COMMENTS = "show_comments"
ISO_8601 = "iso_8601"
MAILTO_AUTHOR = "mailto_author"
CSS_URL = "css_url"
EDIT_ROWS = "edit_rows"
RESULTS_PER_PAGE = "results_per_page"
WANT_TRIVIAL = "want_trivial"
EMAIL_SUBSCRIBED_EVENTS = "email_subscribed_events"
DISABLED = "disabled"
EMAIL_UNVALIDATED = "email_unvalidated"
NAMERE = "namere"
NAMEPREFIX = "nameprefix"

# in which backend is some revision stored?
BACKENDNAME = "backendname"

USEROBJ_ATTRS = [
    # User objects proxy these attributes of the UserProfile objects:
    NAME,
    DISABLED,
    ITEMID,
    DISPLAY_NAME,
    ENC_PASSWORD,
    EMAIL,
    ISO_8601,
    MAILTO_AUTHOR,
    SHOW_COMMENTS,
    RESULTS_PER_PAGE,
    EDIT_ON_DOUBLECLICK,
    SCROLL_PAGE_AFTER_EDIT,
    EDIT_ROWS,
    THEME_NAME,
    LOCALE,
    TIMEZONE,
    SUBSCRIPTIONS,
    QUICKLINKS,
    CSS_URL,
]

# keys for blog homepages
LOGO = "logo"
SUPERTAGS = "supertags"
# keys for blog entries
PTIME = "ptime"

# keys for tickets
EFFORT = "effort"
DIFFICULTY = "difficulty"
SEVERITY = "severity"
PRIORITY = "priority"
ASSIGNED_TO = "assigned_to"
SUPERSEDED_BY = "superseded_by"
DEPENDS_ON = "depends_on"
CLOSED = "closed"
ELEMENT = "element"
REPLY_TO = "reply_to"

# index names
LATEST_REVS = "latest_revs"
ALL_REVS = "all_revs"

# values for ACTION key
ACTION_SAVE = "SAVE"
ACTION_REVERT = "REVERT"
ACTION_TRASH = "TRASH"
ACTION_COPY = "COPY"
ACTION_RENAME = "RENAME"
ACTION_CONVERT = "CONVERT"

# defaul LOCALE key value
DEFAULT_LOCALE = "en"

# key for composite name
FQNAME = "fqname"
FQNAMES = "fqnames"
# Values that FIELD can take in the composite name: [NAMESPACE/][@FIELD/]NAME
FIELDS = [NAME_EXACT, ITEMID, REVID, TAGS, USERID, ITEMLINKS, ITEMTRANSCLUSIONS]
# Fields that can be used as a unique identifier.
UFIELDS = [NAME_EXACT, ITEMID, REVID]
# Unique fields that are stored as list.
UFIELDS_TYPELIST = [NAME_EXACT]
