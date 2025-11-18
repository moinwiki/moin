===========
Development
===========

Useful Resources
================

If you have any questions about MoinWiki you can use the following resources:

Documentation (installation, configuration, user docs, API reference):

* https://moin-20.readthedocs.io/en/latest/

Repository, Issue tracker (bugs, proposals, todo), Code Review, Discussions, etc.:

* https://github.com/moinwiki/moin

Wiki:

* https://moinmo.in/MoinMoin2.0  (production wiki, using moin 1.9)

IRC channel on libera.chat (quick communication and discussion):

* #moin  (Web Chat: https://web.libera.chat/?#moin)


Requirements for development
============================

Git is required if you wish to contribute patches to the Moin2 development effort.
Even if you do not intend to contribute, Git is highly recommended as it
will make it easy for you to obtain fixes and enhancements from the moin2 repositories.
Git can be installed with most Linux package managers or downloaded from https://git-scm.com/.
You can also find many alternative GUI clients there for Unix, macOS and Windows.


Typical development workflow
============================

Once setup is completed, you will have created two repos that work together with the existing
moin master repo hosted on GitHub. One new repo will be a fork of the moin master repo hosted on
GitHub. The other new repo will be a clone of your forked repo that will reside on your
local PC. These three repos will be updated in a cycle:

* keep your cloned repo up to date by pulling changes from the GitHub master repo
* contribute by coding changes in your local cloned repo and pushing to your forked GitHub repo
* after review by an administrator, the new changes in your GItHub forked repo will be merged into
  the moin GitHub master repo
* repeat


create your development environment
-----------------------------------

* if you do not have a GitHub account, create one at https://github.com/
* fork the main repository: https://github.com/moinwiki/moin to your GitHub user account
* clone your GitHub repo to your local development machine::

    cd <parent_directory_of_your_future_repo>
    git clone https://github.com/yourname/moin.git

* cd to repo root::

    cd moin

* create a new venv (Virtual ENVironment) and download packages::

    python quickinstall.py

* activate venv::

    . activate  # Windows: activate

* create a wiki instance and load help data and welcome pages::

    moin create-instance --full

* start the built-in server::

    moin run

* point your browser at http://127.0.0.1:5000/ to access your development wiki
* press Ctrl+C to stop the built-in server

* add the GitHub moin master as a remote, "moinwiki" is used as the remote name below and elsewhere

    git remote add moinwiki https://github.com/moinwiki/moin.git

* verify it works, ensure your local repo up to date

    git pull moinwiki master

add more tools, exercise tools
------------------------------

* install additional software that developers may require::

    ./m extras  # Windows: m extras

* run the unit tests, if there are test failures check for open issues::

    ./m tests  # Windows: m tests

* Node.js and npm are required to install sass. Install Node.js and npm with a
  Linux package manager; Windows users may download both from https://nodejs.org/download/

  * On Ubuntu 14.04 or any distribution based on Ubuntu you need to install "npm" and "nodejs-legacy" (to get the "node" command).

* sass is required to update Basic theme CSS files, install sass::

    sudo npm install -g sass  # Windows: npm install -g sass
    sass --version  # show version number to prove it works

* sass fixup pending resolution of `issue #2043 <https://github.com/moinwiki/moin/issues/2043>`_,
  missing xstatic/pkg/bootstrap/data/scss directory

  - point your browser to https://github.com/twbs/bootstrap/tree/v4.5.3/scss (optional, review before downloading)
  - modify the browser url to https://ssgithub.com/twbs/bootstrap/tree/v4.5.3/scss
  - click the download button to save a zip file to a convenient location
  - unzip the file to xstatic/pkg/bootstrap/data creating a scss directory as a sibling to the existing css and js directories

* regenerate CSS files::

    ./m css  # Windows: m css
    git diff  # verify nothing changed

* check for coding errors (tabs, trailing spaces, line endings, template indentation and spacing)::

    ./m coding-std  # Windows: m coding-std
    git diff  # verify nothing changed

* revert any changes from above::

    git reset --hard

* create local docs::

    ./m docs  # Windows: m docs

* set options on your favorite editor or IDE

  - convert tabs to 4 spaces
  - delete trailing blanks on file save
  - use unix line endings almost everywhere, use Windows line endings on .bat and .cmd files
  - use monospaced font for editing
* if you are new to git, read about it (https://git-scm.com/book/),
  consider printing a cheat sheet
* if you want a Python IDE, try https://www.jetbrains.com/pycharm/ Free Community Edition
* join #moin-dev IRC channel; ask questions, learn what other developers are doing

install pre-commit hooks
------------------------

These tools will inspect your staged changes as part of Git commit processing.

* Black formats Python code to make it consistent and readable according to PEP 8 guidelines.
* Ruff is a linter that detects style issues, errors and potential problems.
* Bandit analyzes the code for possible security vulnerabilities and potential risks.

Setup pre-commit hooks::

    pre-commit install

Running pre-commmit will stash any changed and unstaged files, then black, ruff, and bandit will
examine and report violations on any staged files. Finally, any stashed files will be restored.
Try running pre-commit now::

    pre-commit run

If your code
change violates Black's coding standards (a line of code is > 120 characters) Black will
update the file and fail the commit. Your repo will have 2 versions of the offending file:
the staged file with your changes and an unstaged version with Black's corrections.

To fix, unstage the file to merge your changes into Black's version, then restage the
file and rerun pre-commit.

If Ruff or Bandit find errors, they will create error messages that will cause the commit to fail.
In this case, unstage the offending file, fix the error, restage the file and rerun pre-commit.

Note that these same checks will be made as part of GitHub push-merge processing.
If there is an error the merge will fail. Fix the error, restage the file, and commit.
Next time, remember the easier way is to run pre-commit locally before pushing changes.

Read more about

* Black at https://black.readthedocs.io/en/stable/index.html
* Ruff at https://github.com/astral-sh/ruff?tab=readme-ov-file#ruff
* Bandit at https://bandit.readthedocs.io/en/latest/

review configuration options
----------------------------

* review https://moin-20.readthedocs.io/en/latest/admin/configure.html
* configure options by reading the comments and editing wikiconfig.py

  * the default options in wikiconfig.py are secure, changes are required to edit and save items
  * set superuser privileges on at least one username

find a task to work on
----------------------

* look at the issue tracker to find a task you can solve
* in case you find a new bug or want to work on some (non-trivial) new issue or idea that is
  not on the issue tracker, create an issue with a detailed description
* discuss your chosen task with other developers on the #moin-dev IRC
  channel
* to avoid duplicate work, add a comment on the issue tracker that you are
  working on that issue
* just before you start to code changes, bring your repo up to date::

    git checkout master       # make sure you are on master branch
    git pull moinwiki master  # update your master branch
    git checkout -b mychange  # create a new branch "mychange"

develop a testing strategy
--------------------------

* if you fix something that had no test, first try to write a correct,
  but failing test for it, then fix the code and see a successful test
* if you implement new functionality, write tests for it first, then
  implement it
* when changing a theme, test with multiple browsers

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

  * or, stash your changes and create a new branch to fix the new issue
* regularly run the unit tests ("./m tests"), do not create failing tests

review your working solution
----------------------------

* stage your changed files and do "pre-commit run" to check for style and security issues using Black, Ruff, and Bandit
* do "./m coding-std" to check for coding errors (trailing spaces, template indentation and spacing)
* use git diff, git status - read everything you changed - slowly, look for
  things that can be improved
* look for poor variable names, spelling errors in comments, accidental addition
  or deletion of blank lines, complex code without comments, missing/extra spaces
* if JavaScript files were changed, run https://www.jslint.com/
* run tests again "./m tests"
* do some final testing - edit an item and save, etc.

publish your change
-------------------

* commit your changes to your local repo, use a concise commit comment
  describing the change

  * while a commit message may have multiple lines, many tools show only 80 characters of the first line
  * stuff as much info as possible into those first 80 characters::

        <concise description of your change>, fixes #1234

  * if "fixes #1234" is included in the description, the issue will be closed when your changed is merged into the master
  * if your patch partially fixes an open issue, include the number in the commit message, "#1234"
* push the changeset to your public GitHub repo
* create a pull request so your changes will get reviewed and pulled into the
  main repository
* if you fixed an issue from the issue tracker, be sure the issue gets
  closed after your fix has been pulled into main repo.
* celebrate, loop back to "find a task to work on"

update your venv
----------------

Every week or so, do "./m quickinstall" and "./m extras" to install new releases of
dependent packages. If any new packages are installed, do a
quick check for breakages by running tests, starting the
built-in server, modify an item, etc.


MoinMoin architecture
=====================
moin2 is a WSGI application and uses:

* flask as framework

  - flask cli and click for command line interface
  - flask-babel / babel / pytz for i18n/l10n
  - flask-theme for theme switching
  - flask-caching as cache storage abstraction
* werkzeug for low level web/http page serving, debugging, builtin server, etc.
* jinja2 for templating, such as the theme and user interface
* flatland for form data processing
* EmeraldTree for xml and tree processing
* blinker for signalling
* pygments for syntax highlighting
* for stores: filesystem, sqlite3, sqlalchemy, memory
* jquery javascript lib, a simple jQuery i18n plugin `Plugin <https://github.com/recurser/jquery-i18n>`_
* CKeditor, the GUI editor for (x)html

How MoinMoin works
==================
This is a very high level overview about how moin works. If you would like
to acquire a more in-depth understanding, please read the other docs and code.

WSGI application creation
-------------------------
First, the moin Flask application is created; see `moin.app.create_app`:

* load the configuration (app.cfg)
* register some modules that handle different parts of the functionality

  - moin.apps.frontend - most of what a normal user uses
  - moin.apps.admin - for admins
  - moin.apps.feed - feeds, e.g. atom
  - moin.apps.serve - serving some configurable static third party code
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
  `moin.apps.frontend.show_item`.
* Flask calls the before request handler of this module, which:

  - sets up the user as flaskg.user - an anonymous user or logged in user
  - initializes dicts/groups as flaskg.dicts, flaskg.groups
  - initializes jinja2 environment - templating
* Flask then calls the handler function `moin.apps.frontend.show_item`,
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
`moin.storage.stores`. A store is extremely simple: store a value
for a key and retrieve the value using the key + iteration over keys.

A backend is one layer above. It deals with objects that have metadata and
data, see `moin.storage.backends`.

Above that, there is miscellaneous functionality in `moin.storage.middleware` for:

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
`converters.moinwiki_in`. It then feeds the data of this item into this
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
converters in `moin.converters` supporting different input formats,
dom-dom transformations and output formats.

Templates and Themes
--------------------
Moin uses jinja2 as its templating engine and Flask-Themes as a flask extension to
support multiple themes. There is a ``moin/templates`` directory that contains
a base set of templates designed for the Modernized theme. Other themes may
override or add to the base templates with a directory named ``themes/<theme_name>/templates``.

When rendering a template, the template is expanded within an environment of
values it can use. In addition to this general environment, parameters can
also be given directly to the render call.

Each theme has a ``static/css`` directory. Stylesheets for the Basic theme in
MoinMoin are compiled using the source ``theme.scss`` file in the Basic theme's
``custom`` directory.
::

    ./m css  # Windows: m css

Internationalization in MoinMoin's JS
-------------------------------------
Any string which has to be translated and used in the JavaScript code, has to be defined
at ``moin/templates/dictionary.js``. This dictionary is loaded when the page loads and
the translation for any string can be received by passing it as a parameter to the ``_`` function,
also defined in the same file.

For example, if we add the following to ``i18n_dict`` in ``dictionary.js`` ::

    "Delete this"  : "{{  _("Delete this") }}",

The translated version of "somestring" can be accessed in the JavaScript code by ::

    var a = _("Delete this");


Testing
=======

We use pytest for automated testing. It is currently automatically installed
into your venv as a dependency.

Running the tests
-----------------
To run all the tests, the easiest way is to do::

    ./m tests  # windows:  m tests

To run selected tests, activate your venv and invoke pytest from the
top-level directory::

    pytest --pep8  # run all tests, including pep8 checks
    pytest -rs  # run all tests and output information about skipped tests
    pytest -k somekeyword  # run the tests matching somekeyword only
    pytest --pep8 -k pep8  # runs pep8 checks only
    pytest sometests.py  # run the tests contained in sometests.py

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
Writing tests with `pytest` is easy and has little overhead. Just
use the `assert` statements.

For more information, please read: https://docs.pytest.org/

IDE Setup
---------
Most MoinMoin developers use PyCharm, either the Professional
Edition or the Free Community Edition.  Choose one or the other
and follow the PyCharm setup instructions.

The screenshots below are from Windows 10, using Python 3.10 and
PyCharm Community Edition to debug Moin2 code. *nix setup is similar.

Debug a Transaction
*******************

When setting up the Run/Debug Configurations, it is important to get
the right values for the Script path, Parameters, Python interpreter,
and Working directory.  For general debugging of the moin2 code base
those parameters should be similar to:

.. image:: pycharmA.png
   :alt: pycharm example
   :align: left

If the parameters are correct, then the Run dropdown menu will show green
icons for run and debug. If the only choice under the Run menu is Edit Configuration,
then one of the parameters is wrong, try again. Note: Py``Charm has a tendency
to change the Working Directory field when other values are edited. Be sure it
points to the repo root.

Once the configuration is correct, load a source program, set a break point
and run the debugger. Point your browser to http://127.0.0.1:5000.

Debug a Moin Script
*******************

To debug one of the moin commands that are normally executed in a terminal window,
follow the example below. You can view the list of moin commands by activating
the venv and doing a "moin --help".

.. image:: pycharmB.png
   :alt: pycharm example
   :align: left

Debug a Test
************
To debug a test, start by going to the Py``Charm edit configuration view.
Click the + in the upper left corner to show the popup list of configuration
types. Choose Tox, and then follow the example below for other field values.
Note the test startup will be rather slow; be patient.

.. image:: pycharmC.png
   :alt: pycharm example
   :align: left

Documentation
=============
Moin provides two types of documentation. The Sphinx docs (https://www.sphinx-doc.org)
are written in reST markup, and have a target audience of developers and wiki admins.
The Help docs have a target audience of wiki editors and are written in markups supported by moin.

The Help docs are a minor subset of the Sphinx docs
and may be available in several languages. The Sphinx docs are available only in English.

Sphinx docs are available at https://moin-20.readthedocs.io/en/latest/ or
may be created locally on Moin wiki's installed by developers.
Documentation reST source code, example files and some other text files
are located in the `moin/docs/` directory in the source tree.

Creating local Sphinx docs
--------------------------
Sphinx can create all kinds of documentation formats. The most common are
the local HTML docs that are linked to under the User tab. To generate local docs::

    ./m docs  # Windows: m docs

Loading the Help docs
---------------------
Wiki admins must load the help docs to make them available to editors. Help docs are
located in the `moin/src/moin/help/` directory in the source tree. Most themes
will provide a link to the markup help above the edit textarea or the entire help namespace
may be accessed through the User tab. Write permission to help files is granted by default.
Wiki admins can change permissions via the ACL rules.

To load the help docs::

    moin load-help --namespace help-common  # images common to all languages
    moin load-help --namespace help-en      # English text

Multiple languages may be loaded. Current languages include::

    en

Updating the Help docs
----------------------
Developers may update the help files or add new files through the normal edit process.
When editing is complete run one or more of::

    moin maint-reduce-revisions  # updates all items in all namespaces
    moin maint-reduce-revisions -q <item-name> -n help-en --test true # lists selected items, no updates
    moin maint-reduce-revisions -q <item-name> -n help-en  # updates selected items

Dump all the English help files to the version controlled directory::

    moin dump-help -n help-en

The above command may may be useful after updating one or more files. All of the files
will be rewritten but only the changed files will be highlighted in version control.

Moin Shell
==========

While the make.py utility provides a menu of the most frequently used commands,
there may be an occasional need to access the moin shell directly::

    source <path-to-venv>/bin/activate  # or ". activate"  windows: "activate"
    moin -h                             # show help


Package Release on pypi.org and GitHub Releases
===============================================
* Update docs/changes/CHANGES, run git log and edit results::

    git log --pretty=format:"* %ad %s (%an)" --no-merges --date=short

* Commit or stash all versioned changes.
* Pull all updates from master repo.
* Run `./m quickinstall` and `./m extras` to update the venv and translations.
* Update Development Status, etc. in pyproject.toml
* Run tests.
* Add a signed, annotated tag with the next release number to master branch::

    git tag -s 2.0.0a1 -m "alpha release"

* Install or upgrade release tools::

    pip install --upgrade setuptools wheel
    pip install --upgrade twine
    pip install --upgrade build

* Delete all old releases from the moin/dist directory, else twine will upload them in the next step.

* Build the distribution and upload to pypi.org::

    py -m build > build.log 2>&1  # check build.log for errors
    py -m twine upload dist/*

* Enter ID and password or API Token as requested.

Test Build
----------

Create a new venv, install moin, create instance, start server, create item, modify and save an item::

    <python> -m venv </path/to/new/venv>
    cd </path/to/new/venv>
    source bin/activate  # or "scripts\activate" on windows
    pip install --pre moin
    moin --help  # prove it works
    # update wikiconfig.py  # default allows read-only, admins may load data
    moin create-instance --path <path/to/new/wikiconfig/dir>  # path optional, defaults to CWD
    cd <path/to/new/wikiconfig/dir>  # skip if using default CWD
    moin index-create

    moin welcome  # load welcome page (e.g. Home)
    moin load-help -n help-en # load English help
    moin load-help -n help-common # load help images
    moin run  # wiki with English help and welcome pages

Continue with Package Release
-----------------------------

Push the signed, annotated tag created above to github master::

    git push moinwiki 2.0.0a1

Create an ASCII-format detached signature named moin-2.0.0a1.tar.gz.asc.
Windows developers should use Git-Bash to work around #1723.::

    cd dist
    gpg --detach-sign -a moin-2.0.0a1.tar.gz
    cd ..

Follow the instructions in the url below to update GitHub; drag & drop moin-2.0.0a1.tar.gz
and moin-2.0.0a1.tar.gz.asc to upload files area. These files serve as
a backup for the release sdist and the signature, so anybody can
verify the sdist is authentic::

    https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository

Test the GitHub package release::

    <python> -m venv </path/to/new/venv>
    cd </path/to/new/venv>
    source bin/activate  # or "scripts\activate" on windows
    pip install git+https://github.com/moinwiki/moin@2.0.0a1
    moin --help  # prove it works
    # update wikiconfig.py  # default allows read-only, admins may load data
    moin create-instance --path <path/to/new/wikiconfig/dir>  # path optional, defaults to CWD
    cd <path/to/new/wikiconfig/dir>  # skip if using default CWD
    moin index-create

    moin welcome  # load welcome page (e.g. Home)
    moin load-help -n help-en # load English help
    moin load-help -n help-common # load help images
    moin run  # wiki with English help and welcome pages

Announce update on #moin, moin-devel@python.org, moin-user@python.org::

    Moinmoin 2.0.0a1 has been released on https://pypi.org/project/moin/#history
    and https://github.com/moinwiki/moin/releases. See https://moin-20.readthedocs.io/en/latest/,
    use https://github.com/moinwiki/moin/issues to report bugs.
