import sys
import os
import site

this_dir = os.path.dirname(os.path.abspath(__file__))

site.addsitedir(this_dir + '-venv-python2.7/lib/python2.7/site-packages')

# make sure this directory is in sys.path (.lower() avoids duplicate entries in windows)
if not (this_dir in sys.path or this_dir.lower() in sys.path):
    sys.path.insert(0, this_dir)

wiki_config = this_dir + '/wikiconfig_local.py'
if not os.path.exists(wiki_config):
    wiki_config = this_dir + '/wikiconfig.py'

# application is the Flask application
from moin.app import create_app
application = create_app(wiki_config)
