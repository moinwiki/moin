============
Requirements
============

MoinMoin requires Python >= 2.6 and < 3.0.
We usually test using CPython and this is what we recommend.

You can also try PyPy: PyPy >= 1.6 seems to work with moin.

Servers
=======

For moin, you can use any server compatible with WSGI:

* the builtin "moin" server is recommended for desktop wikis, testing,
  debugging, development, adhoc-wikis, etc.
* apache with mod_wsgi is recommended for bigger/busier wikis.
* other WSGI-compatible servers or middlewares are usable
* Google App Engine (experimental)
* For cgi, fastcgi, scgi, ajp, etc., you can use the "flup" middleware:
  http://trac.saddi.com/flup
* IIS with ISAPI-WSGI gateway is also compatible: http://code.google.com/p/isapi-wsgi/


Dependencies
============

For dependency information, please see setup.py.

If you use easy_install or pip or our ``quickinstall`` script, then
dependencies are usually automatically dealt with. Alternatively, you can
use a support archive that contains all the dependencies.


Clients
=======
On the client side, you need:

* a decent web browser that supports W3C standards HTML 5 and CSS 2.1 as well
  as JavaScript:

  - any current version of Firefox, Chrome, Opera, Safari, Internet Explorer
    (IE9 or IE10) should work.
  - usage of older Internet Explorer versions is not recommended and not
    supported because they are known for causing issues.
    For Windows 7 (or 8) Microsoft provides IE9 or IE10.
* Java browser plugin (optional, needed if you want to use TWikiDraw or
  AnyWikiDraw drawing applets).

