# copyright: 2010 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - mod_wsgi driver script

    To use this, copy this file to your wiki root (wikiconfig.py resides there),
    then add these statements to your Apache's VirtualHost definition:

    WSGIScriptAlias / /<path-to>/moin2wsgi.py
    moin-wsgi user=someuser group=somegroup processes=5 threads=10 maximum-requests=1000 umask=0007
    WSGIProcessGroup moin-wsgi
"""

import sys
import os

from moin.app import create_app

moin_dir = os.path.dirname(os.path.abspath(__file__))

if not (moin_dir in sys.path or moin_dir.lower() in sys.path):
    sys.path.insert(0, moin_dir)

wiki_config = moin_dir + "/wikiconfig.py"

# create the Moin (Flask) WSGI application
application = create_app(wiki_config)

# if you want to do some wsgi app wrapping, do it like shown below:
# application.wsgi_app = somewrapper(application.wsgi_app)
