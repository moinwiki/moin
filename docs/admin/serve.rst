==============
Server options
==============

Built-in Web Server (easy)
==========================
Moin comes with a simple built-in web server powered by Werkzeug, which
is suitable for development, debugging, and personal and small group wikis.

It is *not* made for serving bigger loads, but it is easy to use.

Please note that by default the built-in server uses port 8080. As this is
above port 1024, root (Administrator) privileges are not required and we strongly
recommend that you use a normal, unprivileged user account instead. If you
are running a desktop wiki or doing moin development, then use your normal
login user.

Running the built-in server
---------------------------
Run the moin built-in server as follows::

 # easiest for debugging (single-process, single-threaded server):
 moin

 # required for some browsers like IE9 or Chrome in incognito mode (try this
 # in case you encounter a hanging browser / not responding server):
 moin moin --threaded

 # or, if you need another ip/port:
 moin moin --config /path/to/wikiconfig.py --host 1.2.3.4 --port 7777

While the moin server is starting up, you will see some log output, for example::

 2011-03-06 23:35:11,445 INFO werkzeug:116  * Running on http://127.0.0.1:8080/

Now point your browser at that URL - your moin wiki is running!

Stopping the built-in server
----------------------------
To stop the wiki server, either use `Ctrl-C` or close the window.


External Web Server (advanced)
==============================
We won't go into details about using moin under an external web server, because every web server software is
different and has its own documentation, so please read the documentation that comes with it. Also, in general,
server administration requires advanced experience with the operating system,
permissions management, dealing with security, the server software, etc.

In order to use MoinMoin with another web server, ensure that your web server can talk to the moin WSGI
application, which you can get using this code::

 from MoinMoin.app import create_app
 application = create_app('/path/to/config/wikiconfig.py')

MoinMoin is a Flask application, which is a micro framework for WSGI applications,
so we recommend you read Flask's good deployment documentation.

Make sure you use `create_app()` as shown above to create the application,
because you can't import the application from MoinMoin.

Continue reading here: http://flask.pocoo.org/docs/deploying/

In case you run into trouble with deployment of the moin WSGI application,
you can try a simpler WSGI app first. See `docs/examples/deployment/test.wsgi`.

As long as you can't make `test.wsgi` work, the problem is not with
moin, but rather with your web server and WSGI app deployment method.

When the test app starts doing something other than Server Error 500, please
proceed with the MoinMoin app and its configuration.
Otherwise, read your web server error log files to troubleshoot the issue from there.
