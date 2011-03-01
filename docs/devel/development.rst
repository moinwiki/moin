===========
Development
===========

Project Organisation
====================
We mainly use IRC and the wiki for communication, documentation and
planning.

IRC channels (on chat.freenode.net):

* #moin-dev (core development topics)
* #moin (user support, extensions)

Wikis:

* http://moinmo.in/

Issue tracker:

* http://bitbucket.org/thomaswaldmann/moin-2.0/issues

We use Mercurial DVCS (hg) for distributed version control.

Repositories:

* http://hg.moinmo.in/moin/2.0 (main repository)
* http://bitbucket.org/thomaswaldmann/moin-2.0 (bb mirror for your
  convenience, simplifying forking and contributing)

If you are not using Mercurial, you can of course also just send us patches.


MoinMoin architecture
=====================
moin2 is a WSGI application and uses:

* flask as framework

  - flask-script for commandline scripts
  - flask-babel / babel / pytz / parsedatetime for i18n/l10n
  - flask-themes for theme switching
  - flask-cache as cache storage abstraction
* werkzeug for lowlevel web/http stuff, debugging, builtin server, etc.
* jinja2 for templating (theme, user interface)
* flatland for form data processing
* EmeraldTree for xml / tree processing
* blinker for signalling
* pygments for syntax highlighting
* sqlalchemy as sql database abstraction (for indexing)

  - by default using sqlite as database
* jquery javascript lib
* CKeditor - GUI editor for (x)html
* TWikiDraw, AnyWikiDraw, svgdraw drawing tools

.. todo::

   add some nice gfx


How MoinMoin works
==================
This is just a very high level overview about how moin works, if you'ld like
to know more details, you'll have to read more docs and the code.

WSGI application creation
-------------------------
First, the moin Flask application is created (see `MoinMoin.app.create_app`) -
this will:

* load the configuration (app.cfg)
* register some Modules that handle different parts of the functionality

  - MoinMoin.apps.frontend - most stuff a normal user uses
  - MoinMoin.apps.admin - some stuff for admins
  - MoinMoin.apps.feed - feeds (e.g. atom)
  - MoinMoin.apps.serve - serving some configurable static 3rd party stuff
* register before/after request handlers
* initialize the cache (app.cache)
* initialize the storage (app.storage)
* initialize the translation system
* initialize theme support

This app is then given to a WSGI compatible server somehow and will be called
by the server for each request for it.

Request processing
------------------
Let's look at how it shows a wiki item:

* the Flask app receives a GET request for /WikiItem
* Flask's routing rules determine that this request should be served by
  `MoinMoin.apps.frontend.show_item`.
* Flask calls the before request handler of this module, which:

  - sets up the user as flaskg.user (anon user or logged in user)
  - initializes dicts/groups as flaskg.dicts, flaskg.groups
  - initializes jinja2 environment (templating)
* Flask then calls the handler function `MoinMoin.apps.frontend.show_item`,
  which

  - creates an in-memory Item

    + by fetching the item of name "WikiItem" from storage
    + it looks at the mimetype of this item (stored in metadata)
    + it creates an appropriately typed Item instance (depending on the mimetype)
  - calls Item._render_data() to determine how the rendered item looks like
    as HTML
  - renders the `show_item.html` template (and gives it the rendered item html)
  - returns the result to Flask
* Flask calls the after request handler which does some cleanup
* Flask returns an appropriate response to the server

Storage
-------
Moin supports different storage backends (like storing directly into files /
directories, using Mercurial DVCS, using a SQL database, etc. - see
`MoinMoin.storage.backends`).

All these backends conform to same storage API definition (see
`MoinMoin.storage`), which is used by the higher levels (no matter what
backend is used).

There is also some related code in the storage package for:

* processing ACLs (access control lists, protecting that items get accessed
  by users that are not allowed to)
* router (a fstab like mechanism, so one can mount multiple backends at
  different places in the namespace)
* indexing (putting important metadata into a index database, so finding,
  selecting items is speedier)

DOM based transformations
-------------------------
But how does moin know how the HTML rendering of some item looks like?

Each Item has some mimetype (stored in metadata) - the input mimetype.
We also know what we want as output - the output mimetype.

Moin uses converters to transform the input data into the output data in
multiple steps and has a registry that knows all converters and their supported
input and output mimetypes.

For example, if the mimetype is `text/x-moin-wiki`, it'll find that the input
converter handling this is the one defined in `converter.moinwiki_in`. It then
feeds the data of this item into this converter. The converter parses this
input and creates a in-memory `dom tree` representation from it.

This dom tree is then transformed through multiple dom-to-dom converters for
e.g.:

* link processing
* include processing
* smileys
* macros

Finally, the dom-tree will reach the output converter, which will transform it
into the desired output format, e.g. `text/html`.

This is just one example of a supported transformation, there are quite a lot
of converters in `MoinMoin.converter` supporting different input formats,
dom-dom transformations and output formats.

Templates and Themes
--------------------
Moin uses jinja2 as templating engine and Flask-Themes as a flask extension to
support multiple themes (each themes has static data, like css, and templates).

When rendering a template, the template is expanded within an environment of
values it can use. Additionally to this (general) environment, parameters can
be also given directly to the render call.

Testing
=======

We use py.test for automated testing (it is currently automatically installed
into your virtualenv as a dependency).

Running the tests
-----------------
To run the tests you first need to enter your virtualenv::

    . env/bin/activate

To run tests, enter::

    py.test  # runs all tests
    py.test -k somekeyword  # just run the tests matching somekeyword
    py.test sometests.py  # just run the tests contained in sometests.py

Tests output
------------
Most is quite self-explaining, the characters mean::

    . test ran OK
    s test was skipped
    E error happened while running the test
    F test failed
    x test was expected to fail (xfail)

If something went wrong, you'll also see some traceback and stdout/stderr.

Writing tests
-------------
Writing tests with `py.test` is easy and low on overhead. You basically just
use `assert` statements.

For more information, please read on there: http://pytest.org/ - but keep in
mind that we currently still use **py.test 1.3.4**.

Documentation
=============
We use Sphinx (see http://sphinx.pocoo.org/) and reST markup for documenting
moin. Documentation reST source code, example files and some other text files
are located in the `docs/` directory in the source tree.

Creating docs
-------------
Sphinx can create all kinds of documentation formats, we'll just list the most
popular ones below::

    cd docs
    make html  # create html docs (to browse online or in the filesystem)

