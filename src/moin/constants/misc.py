# Copyright: 2011 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - misc. constants not fitting elsewhere
"""

import re

ANON = "anonymous"

# Invalid characters - invisible characters that should not be in page
# names. Prevent user confusion and wiki abuse, e.g '\u202aFrontPage'.
ITEM_INVALID_CHARS_REGEX = re.compile(
    r"""
    \u0000 | # NULL

    # Bidi control characters
    \u202A | # LRE
    \u202B | # RLE
    \u202C | # PDF
    \u202D | # LRM
    \u202E   # RLM
    """,
    re.UNICODE | re.VERBOSE,
)

CLEAN_INPUT_TRANSLATION_MAP = {
    # these chars will be replaced by blanks
    ord("\t"): " ",
    ord("\r"): " ",
    ord("\n"): " ",
}
for c in (
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11"
    "\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"
):
    # these chars will be removed
    CLEAN_INPUT_TRANSLATION_MAP[ord(c)] = None
del c

# Other stuff
URI_SCHEMES = [
    "http",
    "https",
    "ftp",
    "file",
    "mailto",
    "nntp",
    "news",
    "ssh",
    "telnet",
    "irc",
    "ircs",
    "xmpp",
    "mumble",
    "webcal",
    "ed2k",
    "apt",
    "rootz",
    "gopher",
    "notes",
    "rtp",
    "rtsp",
    "rtcp",
]

# "ok" constants returned by /utils/edit_locking as in: ok, message = edit_utils.xxx()
NO_LOCK = 0  # false, someone else holds lock for current item
LOCKED = 1  # true, current user has obtained or renewed lock
LOCK = "lock"

# Valid views allowed for itemlinks
VALID_ITEMLINK_VIEWS = ["+meta", "+history", "+download", "+highlight", "+slideshow"]

# Transient attribute added/removed to/from flask session. Used when a User Settings
# form creates a flash message but then redirects the page making the flash message a
# very short flash message.
FLASH_REPEAT = "flash_repeat"
