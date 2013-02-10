# Copyright: 2011,2012 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - validation for storage meta / data

validation modes:

trusted == False: for metadata coming from user input (like from web form) -
                  in this mode some values will be forced (e.g. mtime,
                  address, hostname, ...).

trusted == True: for metadata coming from trusted sources (like loading
                 backups, tests, ...)

The mode trusted=True/False and the values for forcing can be given as extra
params to store_revision (see indexing module).

If supplied metadata is missing some values that are required and have sane
defaults, the validators may implant the defaults into the metadata or reject
the data.
"""


from __future__ import absolute_import, division

import time

from flatland import Dict, List, Unset, Boolean, Integer, String

from MoinMoin.constants import keys
from MoinMoin.config import CONTENTTYPE_DEFAULT, CONTENTTYPE_USER

from MoinMoin.util.crypto import make_uuid, UUID_LEN
from MoinMoin.util.mime import Type


class DuckDict(Dict):
    # in duck mode, keys unknown to the schema will not cause errors
    policy = 'duck'


def uuid_validator(element, state):
    """
    a uuid must be a hex unicode string of specific length
    """
    v = element.value
    if not isinstance(v, unicode):
        return False
    if len(v) != UUID_LEN:
        return False
    try:
        int(v, 16)  # is this hex?
        return True
    except ValueError:
        return False


def itemid_validator(element, state):
    """
    an itemid is a uuid that identifies an item
    """
    if not state['trusted'] or element.raw is Unset:
        itemid = state.get(keys.ITEMID)
        if itemid is None:
            # this is first revision of an item
            itemid = make_uuid()
        element.set(itemid)
    return uuid_validator(element, state)


def revid_validator(element, state):
    """
    a revid is a uuid that identifies a revision
    """
    if element.raw is Unset:
        return True  # revid will be autogenerated by store
    return uuid_validator(element, state)


def userid_validator(element, state):
    """
    a userid is a uuid that identifies a user (profile)
    """
    if not state['trusted']:
        userid = state[keys.USERID]
        element.set(userid)
        if userid is None:
            # unknown user is acceptable
            return True
    return uuid_validator(element, state)


def name_validator(element, state):
    """
    a (item/revision) name
    """
    if element.raw is Unset:
        element.set(state[keys.NAME])
    v = element.value
    if not isinstance(v, unicode):
        return False
    if v != v.strip():
        return False
    if v.startswith(u'+'): # used for views, like /+meta/<itemname>
        return False
    if v.endswith(u'/'):
        return False
    return True


def tag_validator(element, state):
    """
    a tag
    """
    if element.raw is Unset:
        return True
    v = element.value
    if not isinstance(v, unicode):
        return False
    if v != v.strip():
        return False
    return True


def wikiname_validator(element, state):
    """
    a wikiname (name of the wiki site)
    """
    if element.raw is Unset:
        element.set(state[keys.WIKINAME])
    return name_validator(element, state)


def namespace_validator(element, state):
    """
    a namespace (part of a wiki site)
    """
    if element.raw is Unset:
        element.set(state[keys.NAMESPACE])
    return name_validator(element, state)


def user_contenttype_validator(element, state):
    """
    user profile content type
    """
    if element.raw is Unset:
        element.set(CONTENTTYPE_USER)
    v = element.value
    if not isinstance(v, unicode):
        return False
    return v == CONTENTTYPE_USER


def contenttype_validator(element, state):
    """
    a supported content type
    """
    if element.raw is Unset:
        ct = state.get('contenttype_current')
        if ct is None:
            ct = state.get('contenttype_guessed')
            if ct is None:
                ct = CONTENTTYPE_DEFAULT
        element.set(ct)
    v = element.value
    if not isinstance(v, unicode):
        return False
    ct = Type(v)
    if ct.type not in ['text', 'image', 'audio', 'video', 'application', ]:
        return False
    if not ct.subtype:
        return False
    if ct.type == 'text':
        charset = ct.parameters.get('charset')
        if charset is None:
            # we must have the charset, otherwise decoding is impossible
            return False
        if charset.lower() not in ['ascii', 'utf-8', ]:
            # currently we do not recode
            return False
    return True


def mtime_validator(element, state):
    """
    a modification time (UNIX timestamp)
    """
    if not state['trusted'] or element.raw is Unset:
        now = int(time.time())
        element.set(now)
    v = element.value
    if not isinstance(v, (int, long)):
        return False
    #if v < 31 * 24 * 3600:
    #    # we don't have negative values nor timestamps from Jan 1970,
    #    # this likely was some crap 0 +/- maybe tz adjustments
    #    return False
    # ^^ TODO: some tests still use 1,2,3,...
    return True


def action_validator(element, state):
    """
    an action
    """
    if not state['trusted']:
        element.value = state[keys.ACTION]
    v = element.value
    if not isinstance(v, unicode):
        return False
    if v not in [u'SAVE', u'REVERT', u'TRASH', u'COPY', u'RENAME', ]:
        return False
    return True


def acl_validator(element, state):
    """
    an acl, also checks if changing acl is allowed
    """
    if element.raw is Unset:
        return True
    if state['trusted']:
        if element.value is None:
            return False
        return True
    else: # untrusted
        v = element.value
        if not isinstance(v, unicode):
            return False
        # TODO check parent revision acl / whether acl would be changed
        #acl_changed = v != state['acl_parent']
        #is_admin = False
        #if acl_changed and not is_admin:
        #    return False
        return True


def comment_validator(element, state):
    """
    a comment
    """
    if element.raw is Unset:
        return True
    v = element.value
    if not isinstance(v, unicode):
        return False
    # TODO: check if comment was somehow invalid, e.g. contained html
    return True


def hostname_validator(element, state):
    """
    a hostname (dns name)
    """
    if not state['trusted']:
        addr = state[keys.ADDRESS]
        element.value = None  # TODO: lookup(addr)
        return True
    v = element.value
    if not isinstance(v, unicode):
        return False
    return True


def address_validator(element, state):
    """
    an IP address
    """
    if not state['trusted']:
        element.value = state[keys.ADDRESS]
    v = element.value
    if not isinstance(v, unicode):
        return False
    return True


def size_validator(element, state):
    """
    a content size
    """
    v = element.value
    if not state['trusted'] and v is None:
        # untrusted size gets overwritten by the real value
        # in the storage code, so everything is acceptable.
        return True
    try:
        element.value = v = int(v)
    except (TypeError, ValueError):
        return False
    if v < 0:
        return False
    return True


def hash_validator(element, state):
    """
    a content hash
    """
    v = element.value
    if not state['trusted'] and v is None:
        # untrusted hash gets overwritten by the real value
        # in the storage code, so everything is acceptable.
        return True
    if not isinstance(v, unicode):
        return False
    if len(v) != keys.HASH_LEN:
        return False
    try:
        int(v, 16)  # is this hex?
        return True
    except ValueError:
        return False

common_meta = (
    String.named(keys.ITEMID).validated_by(itemid_validator),
    String.named(keys.REVID).validated_by(revid_validator),
    String.named(keys.PARENTID).validated_by(uuid_validator).using(optional=True),
    String.named(keys.WIKINAME).using(strip=False).validated_by(wikiname_validator),
    String.named(keys.NAMESPACE).using(strip=False).validated_by(namespace_validator),
    List.named(keys.NAME).of(String.using(strip=False).validated_by(name_validator)),
    List.named(keys.NAME_OLD).of(String.using(strip=False).validated_by(name_validator)).using(optional=True),
    Integer.named(keys.MTIME).validated_by(mtime_validator),
    String.named(keys.ACTION).validated_by(action_validator),
    String.named(keys.ACL).validated_by(acl_validator),
    String.named(keys.COMMENT).validated_by(comment_validator),
    String.named(keys.ADDRESS).validated_by(address_validator),
    String.named(keys.HOSTNAME).validated_by(hostname_validator).using(optional=True),
    List.named(keys.TAGS).of(String.named('tag').validated_by(tag_validator)).using(optional=True),
)

ContentMetaSchema = DuckDict.named('ContentMetaSchema').of(
    String.named(keys.CONTENTTYPE).validated_by(contenttype_validator),
    String.named(keys.USERID).validated_by(userid_validator),
    Integer.named(keys.SIZE).validated_by(size_validator),
    String.named(keys.HASH_ALGORITHM).validated_by(hash_validator),
    String.named(keys.DATAID).validated_by(uuid_validator).using(optional=True),
    # markup items may have this:
    List.named(keys.ITEMLINKS).of(String.named('itemlink').validated_by(wikiname_validator)).using(optional=True),
    List.named(keys.ITEMTRANSCLUSIONS).of(String.named('itemtransclusion').validated_by(wikiname_validator)).using(optional=True),
    # TODO: CONTENT validation? can we do it here?
    *common_meta
)

UserMetaSchema = DuckDict.named('UserMetaSchema').of(
    String.named(keys.CONTENTTYPE).validated_by(user_contenttype_validator),
    String.named('email').using(optional=True),
    String.named('openid').using(optional=True),
    String.named('enc_password').using(optional=True),
    String.named('recoverpass_key').using(optional=True),
    String.named('theme_name').using(optional=True),
    String.named('timezone').using(optional=True),
    String.named('locale').using(optional=True),
    String.named('css_url').using(optional=True),
    Integer.named('results_per_page').using(optional=True),
    Integer.named('edit_rows').using(optional=True),
    Boolean.named('disabled').using(optional=True),
    Boolean.named('want_trivial').using(optional=True),
    Boolean.named('show_comments').using(optional=True),
    Boolean.named('edit_on_doubleclick').using(optional=True),
    Boolean.named('scroll_page_after_edit').using(optional=True),
    Boolean.named('mailto_author').using(optional=True),
    List.named('quicklinks').of(String.named('quicklinks')).using(optional=True),
    List.named('subscribed_items').of(String.named('subscribed_item')).using(optional=True),
    List.named('email_subscribed_events').of(String.named('email_subscribed_event')).using(optional=True),
    #TODO: DuckDict.named('bookmarks').using(optional=True),
    *common_meta
)
