===========
Development
===========

Useful Resources
================

IRC channels on chat.freenode.net (quick communication and discussion):

* #moin-dev  (core development topics)
* #moin  (user support, extensions)

Wikis:

* http://moinmo.in/  (production wiki, using moin 1.9)
* http://test.moinmo.in/  (test wiki, using moin 2)

Documentation (installation, configuration, user docs, api reference):

* http://readthedocs.org/docs/moin-20/en/latest/

Issue tracker (bugs, proposals, todo):

* http://bitbucket.org/thomaswaldmann/moin-2.0/issues

Code Repositories (using Mercurial DVCS http://mercurial.selenic.com/):

* http://hg.moinmo.in/moin/2.0  (main repository)
* http://bitbucket.org/thomaswaldmann/moin-2.0  (bitbucket mirror for your
  convenience, simplifying forking and contributing)

Code review (always use this to get feedback about code changes):

* http://code.google.com/p/rietveld/wiki/CodeReviewHelp
* http://codereview.appspot.com/ (list of current codereview activity)

Pastebin (temporary storage - do not use for code review or any long-term need):

* http://rn0.ru/

Typical development workflow
============================

This is the typical workflow for anyone that wants to contribute to the development of Moin2.

create your development environment
-----------------------------------

* if you do not have a bitbucket account, create one at https://bitbucket.org
* fork the main repository on bitbucket: https://bitbucket.org/thomaswaldmann/moin-2.0
* clone the main repository to your local development machine::

    cd <parent_directory_of_your_future_repo>
    hg clone https://bitbucket.org/thomaswaldmann/moin-2.0 moin-2.0
* ensure you are in default branch::

    hg update default
* create the virtualenv and download packages::

    python quickinstall.py
* create a wiki instance and load sample data::

    ./m sample  # Windows: m sample
* start the built-in server::

    ./m run  # Windows: m run
* point your browser at http://127.0.0.1:8080/ to access your development wiki
* key ctrl+C to stop the built-in server

add more tools, exercise tools
------------------------------

* install additional software that developers may require, including upload.py::

    ./m extras  # Windows: m extras
* if you do not have a google account, create one at http://codereview.appspot.com
* read about code review at: http://code.google.com/p/rietveld/wiki/CodeReviewHelp
* practice using codereview by making a trivial change to any source file, do "python upload.py"

  * inspect your patch set at http://codereview.appspot.com
  * experiment by adding comments, upload a second patchset "python upload.py -i <issue_ID>"
  * revert the changes on your local repo "hg revert --all"

* run the unit tests, note any existing test failures::

     ./m tests  # Windows: m tests

* install NodeJS and NPM with Linux package manager; Windows users may download both from http://nodejs.org/download/

  * On Ubuntu 14.04 you need to install "npm" and "nodejs-legacy" (to get the "node" command).

* install stylus::

    sudo npm install stylus@0.42.2 -g  # Windows: npm install stylus@0.42.2 -g
    # we need 0.42.2 because with more recent versions, --compress compresses
    # complete output to 1 line (0.42.2 compresses to 1 line per rule)
    stylus -V  # show version number to prove it works
* install lessc ("less" below is not a typo)::

    sudo npm install less -g  # Windows: npm install less -g
    lessc --version"  # show version number to prove it works
* regenerate CSS files::

    ./m css  # Windows: m css
    hg diff  # verify nothing changed
* check for coding errors (tabs, trailing spaces, line endings)::

    ./m coding-std  # Windows: m coding-std
    hg diff  # verify nothing changed
* check for uncommitted API doc changes::

    ./m api  # Windows m api
    hg diff  # verify nothing changed
* revert any changes from above::

    hg revert --all

* create local docs::

    ./m docs  # Windows: m docs
* set options on your favorite editor or IDE

  - convert tabs to 4 spaces
  - delete trailing blanks on file save
  - use unix line endings (use Windows line endings on .bat and .cmd files)
  - use mono-spaced font for editing
* if you are new to mercurial, read a tutorial (http://hginit.com/),
  consider printing a cheatsheet
* if you want a Python IDE, try http://www.jetbrains.com/pycharm/ Free Community Edition
* if you want a graphical interface to Mercurial, install SourceTree (best for mac) or TortoiseHG (best for Windows)
* join #moin-dev IRC channel; ask questions, learn what other developers are doing

find a task to work on
----------------------

* look at the issue tracker to find a task you can solve
* in case you want to work on some (non-trivial) new issue or idea that is
  not on the issue tracker, create an issue with a detailed description
* discuss your chosen task with other developers on the #moin-dev IRC
  channel
* to avoid duplicate work, add a comment on the issue tracker that you are
  working on that issue
* just before you start to code changes, update your local repo: "hg pull -u"

develop a testing strategy
--------------------------

* if you fix something that had no test, first try to write a correct,
  but failing test for it, then fix the code and see a successful test
* if you implement new functionality, write tests for it first, then
  implement it
* make a plan for using a browser to test your changes; which wiki pages are
  effected, how many browsers must be tested
* run "./m tests" to determine if there are any existing test failures before you make changes

develop a working solution
--------------------------

* work in your local repo on your local development machine
  (be sure you work in the right branch)
* concentrate on one issue / one topic, create a clean set of changes
  (that means not doing more than needed to fix the issue, but also it
  means fixing the issue completely and everywhere)
* write good, clean, easy-to-understand code
* obey PEP-8
* do not fix or change code unrelated to your task, if you find
  unrelated bugs, create new issues on the tracker
* regularly run the unit tests ("./m tests"), the amount of failing tests
  shall not increase due to your changes

review your working solution
----------------------------

* use hg diff, hg status - read everything you changed - slowly, look for
  things that can be improved

  - if you have TortoiseHG or SourceTree, use those graphical tools to review changes
* look for poor variable names, spelling errors in comments, accidental addition
  or deletion of blank lines, complex code without comments, missing/extra spaces
* fix everything you find before requesting feedback from others
* run tests again "./m tests", check for trailing spaces, line endings "./m coding-std"

get feedback from other developers
----------------------------------

* add changes to codereview: run "python upload.py" in your local repo

  - to update a codereview, "python upload.py -i <issue_ID>"
* carefully review your changes again on codereview

  - if you find errors, delete the patchset, fix and upload again
* if you have questions or want to explain something, add comments and click
  "Publish+Mail Comments"
* post the codereview URL to #moin-dev IRC channel asking for review
* repeat until everybody is happy with your changes

publish your change
-------------------

* do some final testing - practically and using the unit tests
* commit your changes to your local repo, use a concise commit comment
  describing the change

  * if your change fixes a bitbucket issue, include the number as "fixes #nnn" in your commit comment
* pull any changes made by others from the main repo on Bitbucket, then
  merge and commit the merge
* push the changeset to your public bitbucket repo
* create a pull request so your changes will get pulled into the
  main repository
* optionally, request a pull on the IRC channel
* if you fixed an issue from the issue tracker, be sure the issue gets
  closed after your fix has been pulled into main repo.
* celebrate, loop back to "find a task to work on"

update your virtualenv
----------------------

Every week or so, do "m quickinstall" to install new releases of
dependent packages. If any new packages are installed, do a
quick check for breakages by running tests, starting the
build-in server, modify an item, etc.

Alternate contribution workflows
================================
If the above workflow looks like overkill (e.g. for simple changes)
or you can't work with the tools we usually use, then just create or
update an issue on the issue tracker
https://bitbucket.org/thomaswaldmann/moin-2.0/issues)
or join us on IRC #moin-dev.

MoinMoin architecture
=====================
moin2 is a WSGI application and uses:

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
* for stores: filesystem, sqlite3, sqlalchemy, kyoto cabinet/tycoon, mongodb, memory
* jquery javascript lib, a simple jQuery i18n plugin `Plugin <https://github.com/recurser/jquery-i18n>`_
* CKeditor, the GUI editor for (x)html
* TWikiDraw, AnyWikiDraw, svgdraw drawing tools

How MoinMoin works
==================
This is a very high level overview about how moin works. If you would like
to acquire a more in-depth understanding, please read the other docs and code.

WSGI application creation
-------------------------
First, the moin Flask application is created; see `MoinMoin.app.create_app`:

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
Let's look at how it shows a wiki item:

* the Flask app receives a GET request for /WikiItem
* Flask's routing rules determine that this request should be served by
  `MoinMoin.apps.frontend.show_item`.
* Flask calls the before request handler of this module, which:

  - sets up the user as flaskg.user - an anonymous user or logged in user
  - initializes dicts/groups as flaskg.dicts, flaskg.groups
  - initializes jinja2 environment - templating
* Flask then calls the handler function `MoinMoin.apps.frontend.show_item`,
  which:

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

Above that, there is miscellaneous functionality in `MoinMoin.storage.middleware` for:

* routing by namespace to some specific backend
* indexing metadata and data + comfortable and fast index-based access,
  selection and search
* protecting items by ACLs (Access Control Lists)

DOM based transformations
-------------------------
How does moin know what the HTML rendering of an item looks like?

Each Item has some contenttype that is stored in the metadata, also called
the input contenttype.
We also know what we want as output, also called the output contenttype.

Moin uses converters to transform the input data into the output data in
multiple steps. It also has a registry that knows all converters and their supported
input and output mimetypes / contenttypes.

For example, if the contenttype is `text/x-moin-wiki;charset=utf-8`, it will
find that the input converter handling this is the one defined in
`converter.moinwiki_in`. It then feeds the data of this item into this
converter. The converter parses this input and creates an in-memory `dom tree`
representation from it.

This dom tree is then transformed through multiple dom-to-dom converters for example:

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
support multiple themes. There is a ``MoinMoin/templates`` directory that contains a base set of templates designed for the Modernized theme. Other themes may override or add to the base templates with a directory named ``themes/<theme_name>/templates``. 

When rendering a template, the template is expanded within an environment of
values it can use. In addition to this general environment, parameters can
also be given directly to the render call.

Each theme has a ``static/css`` directory. Stylesheets for the Basic theme in MoinMoin are compiled using the source ``theme.less`` file in the Basic theme's ``static/custom-less`` directory. Stylesheets for the Modernized and Foobar themes are compiled using the ``theme.styl files`` in their respective ``static/css/stylus`` directories. To compile CSS for all themes::

    ./m css  # Windows: m css

Internationalization in MoinMoin's JS
-------------------------------------
Any string which has to be translated and used in the JavaScript code, has to be defined 
at ``MoinMoin/templates/dictionary.js``. This dictionary is loaded when the page loads and
the translation for any string can be received by passing it as a parameter to the ``_`` function,
also defined in the same file.

For example, if we add the following to ``i18n_dict`` in ``dictionary.js`` ::
    
    "Delete this"  : "{{  _("Delete this") }}",

The translated version of "somestring" can be accessed in the JavaScript code by ::

    var a = _("Delete this");


Testing
=======

We use py.test for automated testing. It is currently automatically installed
into your virtualenv as a dependency.

Running the tests
-----------------
To run all the tests, the easiest way is to do::

    ./m tests  # windows:  m tests

To run selected tests, activate your virtual env and invoke py.test from the
toplevel directory::

    py.test --pep8  # run all tests, including pep8 checks
    py.test -rs  # run all tests and output information about skipped tests
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

If something goes wrong, you will also see tracebacks in stdout/stderr.

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
Sphinx can create all kinds of documentation formats. The most common are
the local HTML docs that are linked to under the User tab. To generate local docs::

    ./m docs  # Windows: m docs
