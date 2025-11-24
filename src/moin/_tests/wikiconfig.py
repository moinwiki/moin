# Copyright: 2000-2004 by Juergen Hermann <jh@web.de>
# Copyright: 2011-2013 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Test wiki configuration.

Do not change any values without good reason.

We mostly want to have default values here, except for stuff that doesn't
work without setting them (like data_dir).
"""


from os.path import abspath, dirname, join

from moin.config.default import DefaultConfig


class Config(DefaultConfig):
    """
    Default configuration for unit tests.
    """

    wikiconfig_dir = abspath(dirname(__file__))
    instance_dir = join(wikiconfig_dir, "wiki")
    data_dir = join(instance_dir, "data")
    index_storage = "FileStorage", (join(instance_dir, "index"),), {}
    default_acl = None
    default_root = "FrontPage"
    interwikiname = "MoinTest"
    interwiki_map = dict(Self="http://localhost:8080/", MoinMoin="http://moinmo.in/")
    interwiki_map[interwikiname] = "http://localhost:8080/"
    email_tracebacks = False

    password_hasher_config = dict(
        # For tests, use minimal Argon2 parameters for speed
        # DO NOT use these values in production!
        time_cost=1,  # minimum iterations
        memory_cost=8192,  # 8 MiB (minimum recommended is 8 MiB)
        parallelism=1,  # single thread
        hash_len=16,
        salt_len=16,
    )
