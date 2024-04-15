==============
Server Options
==============

Built-in Web Server (easy)
==========================
Moin comes with a simple built-in web server powered by Werkzeug, which
is suitable for development, debugging, and personal and small group wikis.

It is *not* made for serving bigger loads, but it is easy to use.

Please note that by default the built-in server uses port 5000. As this is
above port 1024, root (Administrator) privileges are not required and we strongly
recommend that you use a normal, unprivileged user account instead. If you
are running a desktop wiki or doing moin development, then use your normal
login user.

Running the built-in server
---------------------------
Run the moin built-in server as follows::

 # easiest for debugging (single-process, single-threaded server):
 moin run

 # or, if you need another configuration file, ip address, or port:
 MOINCFG='/path/to/wikiconfig.py'
 moin run --host 1.2.3.4 --port 7777

While the moin server is starting up, you will see some log output, for example::

 INFO werkzeug WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
  * Running on http://127.0.0.1:5000
 INFO werkzeug Press CTRL+C to quit

Now point your browser at that URL - your moin wiki is running!

Stopping the built-in server
----------------------------
To stop the wiki server, either use `Ctrl-C` or close the window.

Debugging with the built-in server
----------------------------------
Werkzeug has a debugger that may be used to analyze tracebacks. As of version 0.11.0,
a pin number is written to the log when the server is started::

  INFO werkzeug:87  * Debugger pin code: 123-456-789

The pin code must be entered once per debugging session. If you will never use the
built-in server for public access, you may disable the pin check by adding::

 WERKZEUG_DEBUG_PIN=off

to your OS's environment variables. See Werkzeug docs for more information.

Using the built-in server for production
----------------------------------------

.. caution:: Using the built-in server for public wikis is not recommended. Should you
 wish to do so, turn off the werkzeug debugger and auto reloader by passing the --no-debugger
 and --no-reload flags. The wikiconfig.py settings of `DEBUG = False` and `TESTING = False` are
 ignored by the built-in server.
 See Werkzeug docs for more information::

  moin run --host 0.0.0.0 --port 80 --no-debugger --no-reload


External Web Server (advanced)
==============================
We won't go into details about using moin under an external web server, because every web server software is
different and has its own documentation, so please read the documentation that comes with it. Also, in general,
server administration requires advanced experience with the operating system,
permissions management, dealing with security, the server software, etc.

In order to use MoinMoin with another web server, ensure that your web server can talk to the moin WSGI
application, which you can get using this code::

 from moin.app import create_app
 application = create_app('/path/to/config/wikiconfig.py')

MoinMoin is a Flask application, which is a micro framework for WSGI applications,
so we recommend you read Flask's good deployment documentation.

Make sure you use `create_app()` as shown above to create the application,
because you can't import the application from MoinMoin.

Continue reading here: https://flask.palletsprojects.com/deploying/

In case you run into trouble with deployment of the moin WSGI application,
you can try a simpler WSGI app first. An example file is included at
`contrib/deployment/test.wsgi`.

As long as you can't make `test.wsgi` work, the problem is not with
moin, but rather with your web server and WSGI app deployment method.

When the test app starts doing something other than Server Error 500, please
proceed with the MoinMoin app and its configuration.
Otherwise, read your web server error log files to troubleshoot the issue from there.

.. tip:: Check contents of /contrib/wsgi/ for sample wsgi files for your server.

Create and Serve a Static Wiki Image
====================================

"dump-html" is a utility used to create static html dumps of MoinMoin wiki content.
You may find it useful to create a static dump for a software release,
a high volume read-only copy for a busy web site, or a
thumb drive version to carry on trips when you do not have internet access.

To execute dump-html, use the command line interface.
The following three commands are equivalent as the
specified options are the defaults. ::

    moin dump-html
    moin dump-html --directory HTML --theme topside_cms --exclude-ns userprofiles --query .*
    moin dump-html -d HTML -t topside_cms -e userprofiles -q .*

The --directory option may be a relative or absolute path. The default directory,
HTML, will be placed under the wiki root.

The --theme option specifies the theme. See "Customize the CMS Theme" within
the "Introduction into MoinMoin Configuration" section for alternatives.

The --exclude-ns option specifies a comma separated list of namespaces that
will be excluded from the dump. The "userprofiles" namespace should always
be excluded. To exclude user home pages from the static dump, use
**userprofiles,users** with no embedded spaces.

The --query option may be a single page name or a regex selecting the items
to be included in the dump. The default of ".*" selects all items.

Once created, the HTML directory may be moved anywhere as all the internal links are
relative. The pages may be served using your favorite web server or directly from
the file system.

.. warning::
 Some browsers (Chrome, IE11, Opera) serve files loaded from the OS
 file system as plain text. https://github.com/moinwiki/moin/issues/641
