==============
Server options
==============

Builtin Web Server (easy)
=========================
Moin comes with a simple builtin web server (provided by werkzeug), which
is suitable for development, debugging, personal and small group wikis.

It is not made for serving bigger loads, but it is easy to use.

Entering the virtual env
------------------------
If you installed to a virtualenv, you need to activate it first, so it will
find the moin script, the moin code and all its library dependencies::

 source env/bin/activate  # for linux (or other posix OSes)
 # or
 call env\bin\activate  # for windows

Running the builtin server
--------------------------
Then you can run the moin builtin server by::

 moin
 # or, if you need another ip/port:
 moin moin --config /path/to/wikiconfig.py --host 1.2.3.4 --port 7777

Now moin starts the builtin server and tries to locate the wiki configuration
from (please use an absolute path):

- commandline argument `--config /path/to/wikiconfig.py`
- environment variable `MOINCFG=/path/to/wikiconfig.py`
- current directory, file `wikiconfig_local.py`
- current directory, file `wikiconfig.py`

While the moin server is starting up, you will see some log output like::

 2011-03-06 23:35:11,445 INFO werkzeug:116  * Running on http://127.0.0.1:8080/

Now point your browser at that URL - your moin wiki is running!

Stopping the builtin server
---------------------------
To stop the wiki server, either use `Ctrl-C` or close the window.


External Web Server (advanced)
==============================
We won't go into details about this, because every web server software is
different and has its own documentation (please read it). Also, in general,
server administration requires advanced experience with the operating system,
permissions management, dealing with security, the server software, etc.

What you need to achieve is that your web server can talk to a WSGI
application. General infos about WSGI can be found on http://wsgi.org/.

For example, for Apache2 there is mod_wsgi, which is a very good choice and
has nice own documentation, see http://code.google.com/p/modwsgi/.

If your web server can't directly talk via WSGI to moin, you maybe want to use
some middleware like flup translating fastcgi, ajp, scgi, cgi to WSGI.
Avoid using cgi, if possible, it is SLOW.
Flup also has its own docs, see http://trac.saddi.com/flup.

test.wsgi first
---------------
The first thing you should get working is the `test.wsgi` we provide (see
`docs/examples/deployment/`). Make sure it works with your server setup (it
will emit some infos about your server / setup).

If `test.wsgi` does not work, you are *not* having a moin problem,
but a problem with your web server (or flup middleware, in case
you use it) or permissions issues or some generic server administration
problem. Please read the appropriate documentation then and after `test.wsgi`
works, please return to here.

moin scripts next
-----------------
OK, so if you got `test.wsgi` working, you'll easily get the moin WSGI app
working, too. Please read the contents of the moin script you want to use (see
`docs/examples/deployment/`), there might be something you need to adapt to
your setup (e.g. pathes to fix).

For Apache2 + mod_wsgi, use `moin.wsgi` (you can also use it as a starting
point for other servers maybe).

If you want to use the `flup` approach, start from `moin.fcgi`.

.. todo:

   Likely moin.fcgi needs testing / fixing.

If it starts doing something else than Server Error 500, please proceed to
MoinMoin configuration.

Otherwise, read your web server error log files.

