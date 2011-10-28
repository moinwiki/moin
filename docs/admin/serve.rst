==============
Server options
==============

Builtin Web Server (easy)
=========================
Moin comes with a simple builtin web server (provided by werkzeug), which
is suitable for development, debugging, personal and small group wikis.

It is not made for serving bigger loads, but it is easy to use.

Please note that by default the builtin server uses port 8080. As this is
>1024, root (Administrator) privileges are not required and we strongly
recommend that you just use a normal (unprivileged) user account. If you
are running a desktop wiki or doing moin development, just use your normal
login user.

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

What you need to achieve is that your web server can talk to the moin WSGI
application, which you can get using this code::

 from MoinMoin.app import create_app
 application = create_app('/path/to/config/wikiconfig.py')

MoinMoin is a Flask application (Flask is a micro framework for WSGI apps),
so we recommend you just read Flask's good deployment documentation.

Just make sure you use `create_app()` as shown above to create the
application (you can't just import the application from MoinMoin).

Continue reading there: http://flask.pocoo.org/docs/deploying/

In case you run into trouble with deployment of the moin WSGI application,
you can try a simpler WSGI app first, see `docs/examples/deployment/test.wsgi`.

As long as you can't make `test.wsgi` work, you do not have a problem with
moin, but with your web server and WSGI app deployment method.

If the test app starts doing something else than Server Error 500, please
proceed with the MoinMoin app and its configuration.
Otherwise, read your web server error log files.

