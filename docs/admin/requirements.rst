============
Requirements
============

MoinMoin requires Python 3.9+. A CPython distribution is
recommended because it will likely be the fastest and most stable.
Most developers use a CPython distribution for testing.
Typical Linux distributions will either have Python 3.9+ installed by
default or will have a package manager that will install Python 3.9+
as a secondary Python.
Windows users may download CPython distributions from https://www.python.org/ or
https://www.activestate.com/.

An alternative implementation of Python, PyPy, is available
from https://www.pypy.org/.


Servers
=======

For Moin2, you can use any server compatible with WSGI:

* the built-in server (used by the "moin run" command) is recommended for
  desktop wikis, testing, debugging, development, ad hoc wikis, etc.
* Apache with mod_wsgi is recommended for bigger/busier wikis.
* Other WSGI-compatible servers or middleware are usable.
* For CGI, FastCGI, SCGI, AJP, etc., you can use the "flup" middleware:
  https://www.saddi.com/software/flup/
* IIS with ISAPI-WSGI gateway is also compatible: https://code.google.com/archive/p/isapi-wsgi


.. caution:: When using the built-in server for public wikis (not recommended), use
        "moin run --no-debugger --no-reload" to turn off the Werkzeug debugger and auto reloader.
        See the Werkzeug docs for more information.


Dependencies
============

Dependent packages will be automatically downloaded and installed during the
Moin2 installation process. For a list of dependencies, see pyproject.toml.


Clients
=======
On the client side, you need a web browser that supports W3C standards HTML 5, CSS 2.1, and JavaScript:

* any current version of Firefox, Chrome, Opera, Safari, Maxthon, Internet Explorer (IE9 or newer).
* use of older Internet Explorer versions is not recommended and not supported.
