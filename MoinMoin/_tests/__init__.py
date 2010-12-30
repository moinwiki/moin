# Copyright: 2007 MoinMoin:KarolNowak
# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2008, 2010 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - some common code for testing
"""


import os, shutil

from flask import current_app as app
from flask import g as flaskg

from MoinMoin import config, security, user
from MoinMoin.items import Item
from MoinMoin.util import random_string
from MoinMoin.storage.error import ItemAlreadyExistsError

# Promoting the test user -------------------------------------------
# Usually the tests run as anonymous user, but for some stuff, you
# need more privs...

def become_valid(username=u"ValidUser"):
    """ modify flaskg.user to make the user valid.
        Note that a valid user will only be in ACL special group "Known", if
        we have a user profile for this user as the ACL system will check if
        there is a userid for this username.
        Thus, for testing purposes (e.g. if you need delete rights), it is
        easier to use become_trusted().
    """
    flaskg.user.name = username
    flaskg.user.may.name = username
    flaskg.user.valid = 1


def become_trusted(username=u"TrustedUser"):
    """ modify flaskg.user to make the user valid and trusted, so it is in acl group Trusted """
    become_valid(username)
    flaskg.user.auth_method = app.cfg.auth_methods_trusted[0]


def become_superuser(username=u"SuperUser"):
    """ modify flaskg.user so it is in the superusers list,
        also make the user valid (see notes in become_valid()),
        also make the user trusted (and thus in "Trusted" ACL pseudo group).

        Note: being superuser is completely unrelated to ACL rights,
              especially it is not related to ACL admin rights.
    """
    become_trusted(username)
    if username not in app.cfg.superusers:
        app.cfg.superusers.append(username)

# Creating and destroying test items --------------------------------
def update_item(name, revno, meta, data):
    """ creates or updates an item  """
    if isinstance(data, unicode):
        data = data.encode(config.charset)
    try:
        item = flaskg.storage.create_item(name)
    except ItemAlreadyExistsError:
        item = flaskg.storage.get_item(name)

    rev = item.create_revision(revno)
    for key, value in meta.items():
        rev[key] = value
    if not 'name' in rev:
        rev['name'] = name
    if not 'mimetype' in rev:
        rev['mimetype'] = u'application/octet-stream'
    rev.write(data)
    item.commit()
    return item

def create_random_string_list(length=14, count=10):
    """ creates a list of random strings """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return [u"%s" % random_string(length, chars) for counter in range(count)]

def nuke_item(name):
    """ complete destroys an item """
    item = Item.create(name)
    item.destroy()
