# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Miscellaneous constants not fitting elsewhere.
"""

from __future__ import annotations

ANON = "anonymous"

# Other stuff

# Whitelist of URI schemes that are deemed safe.
# For security reasons, only URIs with these schemes are turned to
# "active" links when rendering wiki markup (moin, rST, ...).
URI_SCHEMES = [
    "apt",
    "ed2k",
    "file",
    "ftp",
    "gopher",
    "http",
    "https",
    "irc",
    "ircs",
    "mailto",
    "mumble",
    "news",
    "nntp",
    "notes",
    "rootz",
    "rtcp",
    "rtp",
    "rtsp",
    "ssh",
    "telnet",
    "webcal",
    "xmpp",
]

# "ok" constants returned by /utils/edit_locking as in: ok, message = edit_utils.xxx()
NO_LOCK = 0  # false, someone else holds lock for current item
LOCKED = 1  # true, current user has obtained or renewed lock
LOCK = "lock"

# Transient attribute added/removed to/from flask session. Used when a User Settings
# form creates a flash message but then redirects the page making the flash message a
# very short flash message.
FLASH_REPEAT = "flash_repeat"

# Icon class to endpoint mapping used in navbars
ICON_MAP = {
    "admin.index": "fa fa-cog",
    "admin.index_user": "fa fa-user",
    "frontend.backrefs": "fa fa-share",
    "frontend.convert_item": "fa fa-clone",
    "frontend.copy_item": "fa fa-comment",
    "frontend.delete_item": "fa fa-trash",
    "frontend.destroy_item": "fa fa-fire",
    "frontend.download_item": "fa fa-download",
    "frontend.global_history": "fa fa-history",
    "frontend.global_index": "fa fa-list-alt",
    "frontend.global_tags": "fa fa-tag",
    "frontend.highlight_item": "fa fa-code",
    "frontend.history": "fa fa-history",
    "frontend.index": "fa fa-list-alt",
    "frontend.modify_item": "fa fa-pencil",
    "frontend.quicklink_item": "fa fa-star",
    "frontend.rename_item": "fa fa-i-cursor",
    "frontend.show_item": "fa fa-eye",
    "frontend.show_item_meta": "fa fa-table",
    "frontend.similar_names": "fa fa-search-minus",
    "frontend.sitemap": "fa fa-sitemap",
    "frontend.subscribe_item": "fa fa-envelope",
    "frontend.tags": "fa fa-tag",
    "special.comments": "fa fa-comment",
    "special.supplementation": "fa fa-comments",
    "special.transclusions": "fa fa-object-group",
}
