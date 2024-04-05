# Copyright: 2007 MoinMoin:KarolNowak
# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2008, 2010 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - some common code for testing
"""


import socket
from io import BytesIO
from pathlib import Path
import psutil

from flask import g as flaskg

from moin.constants.contenttypes import CHARSET
from moin.constants.keys import NAME, CONTENTTYPE, NAME_EXACT
from moin.converters import include  # noqa prevent circular import
from moin.items import Item
from moin.utils.crypto import random_string
from moin.utils.interwiki import CompositeName


# Promoting the test user -------------------------------------------
# Usually the tests run as anonymous user, but for some stuff, you
# need more privs...


def become_valid(username="ValidUser"):
    """modify flaskg.user to make the user valid.
    Note that a valid user will only be in ACL special group "Known", if
    we have a user profile for this user as the ACL system will check if
    there is a userid for this username.
    Thus, for testing purposes (e.g. if you need delete rights), it is
    easier to use become_trusted().
    """
    flaskg.user.profile[NAME] = [username]
    flaskg.user.may.names = [username]  # see security.DefaultSecurityPolicy class
    flaskg.user.valid = 1


def become_trusted(username="TrustedUser"):
    """modify flaskg.user to make the user valid and trusted, so it is in acl group Trusted"""
    become_valid(username)
    flaskg.user.trusted = True


# Creating and destroying test items --------------------------------


def update_item(name, meta, data):
    """creates or updates an item"""
    if isinstance(data, str):
        data = data.encode(CHARSET)
    fqname = CompositeName("", NAME_EXACT, name)
    item = flaskg.storage.get_item(**fqname.query)

    meta = meta.copy()
    if NAME not in meta:
        meta[NAME] = [name]
    if CONTENTTYPE not in meta:
        meta[CONTENTTYPE] = "application/octet-stream"
    rev = item.store_revision(meta, BytesIO(data), return_rev=True)
    return rev


def create_random_string_list(length=14, count=10):
    """creates a list of random strings"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [f"{random_string(length, chars)}" for counter in range(count)]


def nuke_item(name):
    """complete destroys an item"""
    item = Item.create(name)
    item.destroy()


def check_connection(port, host="127.0.0.1"):
    """
    Check if we can make a connection to host:port.

    If not, raise Exception with a meaningful msg.
    """
    try:
        s = socket.create_connection((host, port))
        s.shutdown(socket.SHUT_RDWR)
        s.close()
    except OSError as err:
        raise Exception(f"connecting to {host}:{port:d}, error: {err!s}")


def get_dirs(subdir: str) -> tuple[Path, Path]:
    """return Paths for directories used in tests creating artifacts_dir if needed

    :param subdir: subdirectory for artifacts_dir
    :returns: tuple (moin_dir, artifacts_dir)
              where moin_dir is Path to moin directory, parent of src
              and artifacts_dir is Path to moin/_test_artifacts/{subdir}"""
    my_dir = Path(__file__).parent.resolve()
    moin_dir = my_dir.parents[2]
    artifacts_dir = moin_dir / "_test_artifacts" / subdir
    if not artifacts_dir.exists():
        artifacts_dir.mkdir(parents=True)
    return moin_dir, artifacts_dir


def get_open_wiki_files():
    proc = psutil.Process()
    files = [f for f in proc.open_files() if "wiki" in f.path]
    for file in files:
        print(f"open wiki {file}")
    return files
