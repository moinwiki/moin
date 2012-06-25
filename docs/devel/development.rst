===========
Development
===========

Project Organisation
====================
We mainly use IRC and the wiki for communication, documentation and planning.

IRC channels on chat.freenode.net::

* #moin-dev (core development topics)
* #moin (user support, extensions)

Wikis::

* http://moinmo.in/

Documentation::

* http://readthedocs.org/docs/moin-20/en/latest/

Issue tracker::

* http://bitbucket.org/thomaswaldmann/moin-2.0/issues

Code Repositories::

* http://hg.moinmo.in/moin/2.0 - main repository
* http://bitbucket.org/thomaswaldmann/moin-2.0 - bitbucket mirror for your
  convenience, simplifying forking and contributing

We use Mercurial DVCS for distributed version control.

If you are not using Mercurial, you can still submit patches.
In that case, open an issue in the issue tracker and attach the patch there.

Code review::

Please use http://codereview.appspot.com/ for getting feedback on moin-related
code, especially if you want to contribute or publish that code.

If you are using a local mercurial repository/workdir, you can very easily
upload your uncommitted workdir state to codereview using their "upload.py".

Then just ask on the IRC channel for review and provide the codereview URL.

MoinMoin architecture
=====================
moin2 is a WSGI application and uses::

* flask as framework

  - flask-script for command line scripts
  - flask-babel / babel / pytz for i18n/l10n
  - flask-themes for theme switching
  - flask-cache as cache storage abstraction
* werkzeug for low level web/http page serving, debugging, builtin server, etc.
* jinja2 for templating, such as the theme and user interface
* flatland for form data processing
* EmeraldTree for xml and tree processing
* blinker for signalling
* pygments for syntax highlighting
* for stores: filesystem, sqlite3, sqlalchemy, kyoto cabinet/tycoon, memory
* jquery javascript lib
* CKeditor, the GUI editor for (x)html
* TWikiDraw, AnyWikiDraw, svgdraw drawing tools

.. todo::

   add some nice gfx


How MoinMoin works
==================
This is a very high level overview about how moin works. If you would like
to acquire a more in-depth understanding, please read the other docs and code.

WSGI application creation
-------------------------
First, the moin Flask application is created; see `MoinMoin.app.create_app`::

* load the configuration (app.cfg)
* register some modules that handle different parts of the functionality

  - MoinMoin.apps.frontend - most of what a normal user uses
  - MoinMoin.apps.admin - for admins
  - MoinMoin.apps.feed - feeds, e.g. atom
  - MoinMoin.apps.serve - serving some configurable static third party code
* register before/after request handlers
* initialize the cache (app.cache)
* initialize index and storage (app.storage)
* initialize the translation system
* initialize theme support

This app is then given to a WSGI compatible server somehow and will be called
by the server for each request for it.

Request processing
------------------
Let's look at how it shows a wiki item::

* the Flask app receives a GET request for /WikiItem
* Flask's routing rules determine that this request should be served by
  `MoinMoin.apps.frontend.show_item`.
* Flask calls the before request handler of this module, which::

  - sets up the user as flaskg.user - an anonymous user or logged in user
  - initializes dicts/groups as flaskg.dicts, flaskg.groups
  - initializes jinja2 environment - templating
* Flask then calls the handler function `MoinMoin.apps.frontend.show_item`,
  which::

  - creates an in-memory Item

    + by fetching the item of name "WikiItem" from storage
    + it looks at the contenttype of this item, which is stored in the metadata
    + it creates an appropriately typed Item instance, depending on the contenttype
  - calls Item._render_data() to determine what the rendered item looks like
    as HTML
  - renders the `show_item.html` template and returns the rendered item html
  - returns the result to Flask
* Flask calls the after request handler which does some cleanup
* Flask returns an appropriate response to the server

Storage
-------
Moin supports different stores, like storing directly into files /
directories, using key/value stores, using an SQL database etc, see
`MoinMoin.storage.stores`. A store is extremely simple: store a value
for a key and retrieve the value using the key + iteration over keys.

A backend is one layer above. It deals with objects that have metadata and
data, see `MoinMoin.storage.backends`.

Above that, there is miscellaneous functionality in `MoinMoin.storage.middleware` for::

* routing by name to some specific backend, like fstab / mount
* indexing metadata and data + comfortable and fast index-based access,
  selection and search
* protecting items by ACLs (Access Control Lists)

DOM based transformations
-------------------------
How does moin know what the HTML rendering of an item looks like?

Each Item has some contenttype that is stored in the metadata, also called the input contenttype.
We also know what we want as output, also called the output contenttype.

Moin uses converters to transform the input data into the output data in
multiple steps. It also has a registry that knows all converters and their supported
input and output mimetypes / contenttypes.

For example, if the contenttype is `text/x-moin-wiki;charset=utf-8`, it will
find that the input converter handling this is the one defined in
`converter.moinwiki_in`. It then feeds the data of this item into this
converter. The converter parses this input and creates an in-memory `dom tree`
representation from it.

This dom tree is then transformed through multiple dom-to-dom converters for example::

* link processing
* include processing
* smileys
* macros

Finally, the dom-tree will reach the output converter, which will transform it
into the desired output format, such as `text/html`.

This is just one example of a supported transformation. There are quite a few 
converters in `MoinMoin.converter` supporting different input formats,
dom-dom transformations and output formats.

Templates and Themes
--------------------
Moin uses jinja2 as its templating engine and Flask-Themes as a flask extension to
support multiple themes, each theme has static data like css and templates.

When rendering a template, the template is expanded within an environment of
values it can use. In addition to this general environment, parameters can
also be given directly to the render call.

Testing
=======

We use py.test for automated testing. It is currently automatically installed
into your virtualenv as a dependency.

Running the tests
-----------------
To run the tests, activate your virtual env and invoke py.test from the
toplevel directory::

    make test  # easiest way (all tests, pep8, skipped info)
    py.test --pep8  # run all tests, including pep8 checks
    py.test -rs  # run all tests and outputs information about skipped tests
    py.test -k somekeyword  # run the tests matching somekeyword only
    py.test --pep8 -k pep8  # runs pep8 checks only
    py.test sometests.py  # run the tests contained in sometests.py

Tests output
------------
Most output is quite self-explanatory. The characters mean::

    . test ran OK
    s test was skipped
    E error happened while running the test
    F test failed
    x test was expected to fail (xfail)

If something went wrong, you will also see some traceback and stdout/stderr.

Writing tests
-------------
Writing tests with `py.test` is easy and has little overhead. Just
use the `assert` statements.

For more information, please read: http://pytest.org/

Documentation
=============
Sphinx (http://sphinx.pocoo.org/) and reST markup are used for documenting
moin. Documentation reST source code, example files and some other text files
are located in the `docs/` directory in the source tree.

Creating docs
-------------
Sphinx can create all kinds of documentation formats. The most
popular ones are::

    cd docs
    make html  # create html docs (to browse online or in the filesystem)

