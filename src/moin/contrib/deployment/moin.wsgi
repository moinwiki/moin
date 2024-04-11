# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - mod_wsgi driver script

    To use this, add those statements to your Apache's VirtualHost definition:
    
    # you will invoke your moin wiki at the root url, like http://servername/ItemName:
    WSGIScriptAlias / /some/path/moin.wsgi

    # create some wsgi daemons - use someuser.somegroup same as your data_dir:
    WSGIDaemonProcess moin-wsgi user=someuser group=somegroup processes=5 threads=10 maximum-requests=1000 umask=0007

    # use the daemons we defined above to process requests!
    WSGIProcessGroup moin-wsgi

    @copyright: 2010 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

# hint: use None as value if the code already is in sys.path
moin_code = None  # '/path/to/code'

wiki_config = "/path/to/config/wikiconfig.py"

import sys, os

if moin_code:
    # add the parent dir of the MoinMoin code to sys.path,
    # to make import work:
    sys.path.insert(0, moin_code)

# application is the Flask application
from moin.app import create_app

application = create_app(wiki_config)

# please note: if you want to do some wsgi app wrapping, do it like shown below:
# application.wsgi_app = somewrapper(application.wsgi_app)
