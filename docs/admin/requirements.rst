============
Requirements
============

MoinMoin requires Python >= 2.6 and < 3.0.

Python build options (in case you have to build your own Python):

* zlib support (required)
* ucs4 (32bit unicode, recommended)
* ucs2 also works for most users (not recommended)


Servers
=======

You can use anything that speaks WSGI to moin:

* the builtin "moin" server (recommended for desktop wikis, testing,
  debugging, development, adhoc-wikis)
* apache with mod_wsgi (recommended for bigger/busier wikis)
* For cgi, fastcgi, scgi, ajp, ... you can use the "flup" middleware:
  http://trac.saddi.com/flup
* IIS with ISAPI-WSGI gateway: http://code.google.com/p/isapi-wsgi/
* other WSGI-compatible servers or middlewares


Dependencies (Python code)
==========================

For dependency information of python libs, please see setup.py.

If you use easy_install or pip (or our ``quickinstall`` script),
this is usually automatically dealt with.


Dependencies (static files)
===========================

This is stuff like javascript, java applets, etc.

If you use our ``quickinstall`` script, this is usually automatically dealt
with.

If you are a Linux distributor you may want to package this software
separately and adapt wikiconfig.py (or the defaults in
MoinMoin/config/default.py).

TWikiDrawPlugin
---------------
Modified version, available at
http://static.moinmo.in/files/packages/TWikiDrawPlugin-moin.tar.gz

svg-edit
--------
2.5 slightly modified, available at
http://static.moinmo.in/files/packages/svg-edit.tar.gz

ckeditor
--------
3.3.1 works, use dist package or download at homepage.

anywikidraw
-----------
0.14 works, use dist package or download at homepage.

JQuery
------
1.4.2 works, use dist package or download at homepage.

