# -*- coding: utf-8 -*-
"""MoinMoin Wiki - Configuration"""

import sys, os

from MoinMoin.config.default import DefaultConfig
from MoinMoin.storage.backends import create_simple_mapping
from MoinMoin.util.interwiki import InterWikiMap


class Config(DefaultConfig):
    # vvv DON'T TOUCH THIS EXCEPT IF YOU KNOW WHAT YOU DO vvv
    # Directory containing THIS wikiconfig:
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))

    # We assume this structure for a simple "unpack and run" scenario:
    # wikiconfig.py
    # wiki/
    #      data/
    # contrib/
    #      xml/
    #          preloaded_items.xml
    # If that's not true, feel free to adjust the pathes.
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data') # Note: this used to have a trailing / in the past
    index_dir = os.path.join(instance_dir, "index")
    index_dir_tmp = os.path.join(instance_dir, "index_tmp")
    wiki_name = u"test_wiki"
    # This puts the contents from the specified xml file (a serialized backend) into your
    # backend(s). You can remove this after the first request to your wiki or
    # from the beginning if you don't want to use this feature at all.
    load_xml = os.path.join(wikiconfig_dir, 'contrib', 'xml', 'preloaded_items.xml')
    #save_xml = os.path.join(wikiconfig_dir, 'contrib', 'xml', 'saved_items.xml')

    # This provides a simple default setup for your backend configuration.
    # 'fs:' indicates that you want to use the filesystem backend. You can also use
    # 'hg:' instead to indicate that you want to use the mercurial backend.
    # Alternatively you can set up the mapping yourself (see HelpOnStorageConfiguration).
    namespace_mapping, router_index_uri = create_simple_mapping(
                            backend_uri='fs2:%s/%%(nsname)s' % data_dir,
                            # XXX we use rather relaxed ACLs for the development wiki:
                            content_acl=dict(before=u'',
                                             default=u'All:read,write,create,destroy,admin',
                                             after=u'', ),
                            user_profile_acl=dict(before=u'',
                                             default=u'All:read,write,create,destroy,admin',
                                             after=u'', ),
                            )

    # Load the interwiki map from intermap.txt:
    interwiki_map = InterWikiMap.from_file(os.path.join(wikiconfig_dir, 'contrib', 'interwiki', 'intermap.txt')).iwmap

    sitename = u'My MoinMoin'

    # for now we load some 3rd party stuff from the place within moin where it is currently located,
    # but soon we'll get rid of this stuff:
    env_dir = 'env'
    serve_files = dict(
        docs = os.path.join(wikiconfig_dir, 'docs', '_build', 'html'),
    )

    # we slowly migrate all stuff from above (old) method, to xstatic (new) method,
    # see https://bitbucket.org/thomaswaldmann/xstatic for details:
    from xstatic.main import XStatic
    mod_names = ['jquery', 'jquery_file_upload', 'ckeditor', 'svgweb', 'svgedit_moin', 'twikidraw_moin', 'anywikidraw', 'mathjax', ]
    pkg = __import__('xstatic.pkg', fromlist=mod_names)
    for mod_name in mod_names:
        mod = getattr(pkg, mod_name)
        xs = XStatic(mod, root_url='/static', provider='local', protocol='http')
        serve_files.update([(xs.name, xs.base_dir)])

    # ^^^ DON'T TOUCH THIS EXCEPT IF YOU KNOW WHAT YOU DO ^^^

    #item_root = u'Home' # change to some better value


MOINCFG = Config # Flask only likes uppercase stuff
# Flask settings - see the flask documentation about their meaning
SECRET_KEY = 'you need to change this so it is really secret'
#DEBUG = False # use True for development only, not for public sites!
#TESTING = False
#SESSION_COOKIE_NAME = 'session'
#PERMANENT_SESSION_LIFETIME = timedelta(days=31)
#USE_X_SENDFILE = False
#LOGGER_NAME = 'MoinMoin'
#config for flask-cache:
#CACHE_TYPE = 'filesystem'
#CACHE_DIR = '/path/to/flask-cache-dir'

# DEVELOPERS! Do not add your configuration items here - you could accidentally
# commit them! Instead, create a wikiconfig_local.py file containing this:
#
#from wikiconfig_editme import *
#
# In wikiconfig_editme.py (the indirection is needed so that the auto reload
# mechanism of the builtin server works) you do this:
#
#from wikiconfig import *
#
#class LocalConfig(Config):
#    configuration_item_1 = 'value1'
#
#MOINCFG = LocalConfig
#DEBUG = True

