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
* other WSGI-compatible servers or middlewares
* For cgi, fastcgi, scgi, ajp, ... you can use the "flup" middleware:
  http://trac.saddi.com/flup
* IIS with ISAPI-WSGI gateway: http://code.google.com/p/isapi-wsgi/


Dependencies
============

For dependency informations, please see setup.py.

If you use easy_install or pip (or our ``quickinstall`` script),
dependencies are usually automatically dealt with.

