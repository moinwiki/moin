============
Requirements
============

MoinMoin requires Python >= 2.6 and < 3.0.
We usually test using CPython and this is what we recommend.

You can also try PyPy: PyPy >= 1.6 seems to work well with moin.
In order to use PyPy, modify the quickinstall script so that the `PYTHON` variable equals `pypy`, i.e. PYTHON=pypy.

Servers
=======

You can use any server compatible with WSGI with moin. Examples:

* the builtin "moin" server is recommended for desktop wikis, testing,
  debugging, development, adhoc-wikis, etc.
* apache with mod_wsgi is recommended for bigger/busier wikis.
* other WSGI-compatible servers or middlewares are usable
* For cgi, fastcgi, scgi, ajp, etc., you can use the "flup" middleware:
  http://trac.saddi.com/flup
* IIS with ISAPI-WSGI gateway is also compatible: http://code.google.com/p/isapi-wsgi/


Dependencies
============

For dependency information, please see setup.py.

If you use easy_install or pip (or our ``quickinstall`` script),
dependencies are usually automatically dealt with.

