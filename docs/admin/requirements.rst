============
Requirements
============

MoinMoin requires Python >= 2.6 and < 3.0.
We usually test using CPython and this is what we recommend.

You can also try PyPy - PyPy >= 1.6 seems to work OK with moin.
Hint: modify the quickinstall script so it uses PYTHON=pypy.

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

