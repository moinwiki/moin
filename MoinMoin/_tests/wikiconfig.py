# Copyright: 2000-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2011-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - test wiki configuration

Do not change any values without good reason.

We mostly want to have default values here, except for stuff that doesn't
work without setting them (like data_dir).
"""


import os
from os.path import abspath, dirname, join

from MoinMoin.config.default import DefaultConfig


class Config(DefaultConfig):
    """
    default configuration for the unit tests
    """
    _here = abspath(dirname(__file__))
    _root = abspath(join(_here, '..', '..'))
    data_dir = join(_here, 'wiki', 'data')  # needed for plugins package TODO
    index_storage = 'FileStorage', (join(_here, 'wiki', 'index'), ), {}
    content_acl = None
    item_root = 'FrontPage'
    interwikiname = u'MoinTest'
    interwiki_map = dict(Self='http://localhost:8080/', MoinMoin='http://moinmo.in/')
    interwiki_map[interwikiname] = 'http://localhost:8080/'

    passlib_crypt_context = dict(
        schemes=["sha512_crypt", ],
        # for the tests, we don't want to have varying rounds
        sha512_crypt__vary_rounds=0,
        # for the tests, we want to have a rather low rounds count,
        # so the tests run quickly (do NOT use low counts in production!)
        sha512_crypt__default_rounds=1001,
    )
