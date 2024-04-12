#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    MoinMoin - CGI/FCGI Driver script

    @copyright: 2000-2005 by Juergen Hermann <jh@web.de>,
                2008-2011 by MoinMoin:ThomasWaldmann,
                2008 by MoinMoin:FlorianKrupicka,
                2010 by MoinMoin:RadomirDopieralski
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

## this works around a bug in flup's CGI autodetection (as of flup 1.0.1):
# os.environ['FCGI_FORCE_CGI'] = 'Y' # 'Y' for (slow) CGI, 'N' for FCGI

# Creating the Moin (Flask) WSGI application
from moin.app import create_app

application = create_app(wiki_config)


class FixScriptName(object):
    """This middleware fixes the script_name."""

    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = self.script_name
        return self.app(environ, start_response)


# Use None if your url looks like http://domain/wiki/moin.fcgi
# Use '' if you use rewriting to run at http://domain/
# Use '/mywiki' if you use rewriting to run at http://domain/mywiki/
fix_script_name = None  # <-- adapt here as needed

if fix_script_name is not None:
    application.wsgi_app = FixScriptName(application.wsgi_app, fix_script_name)

# CGI with Apache2 on Windows (maybe other combinations also) has trouble with
# URLs of non-ASCII pagenames. Use True to enable middleware that tries to fix.
fix_apache_win32 = False  # <-- adapt here as needed

if fix_apache_win32:
    from werkzeug.contrib.fixers import PathInfoFromRequestUriFix

    application.wsgi_app = PathInfoFromRequestUriFix(application.wsgi_app)

# there are also some more fixers in werkzeug.contrib.fixers - see there
# if the stuff above is not enough for your setup.

## Choose your server mode (threaded, forking or single-thread)
from flup.server.fcgi import WSGIServer

# from flup.server.fcgi_fork import WSGIServer
# from flup.server.fcgi_single import WSGIServer

WSGIServer(application).run()
