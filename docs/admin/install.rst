============
Installation
============

Installing the code
===================
There are a lot of ways to do this and as this is not moin specific,
we won't go into details:

- Use your operating system's / distribution's package manager to install the
  moin2 package. This is the recommended method as it will install moin2 and
  all other software it requires. Also your OS / dist might have a mechanism
  for updating the installed software with security fixes or to future releases.

  E.g. on Debian/Ubuntu Linux: ``apt install moin2``
- Install from PyPI: ``pip install moin2``

  - Optionally, create a virtual env first for better separation or
  - use ``pip install --user moin2`` to install into your home directory.
  - pip will automatically install other python packages moin2 requires,
    but you maybe have to install required non-python packages yourself.
  - You will have to care for updates / installing security fixes yourself.

After this, you should have a ``moin`` command available, try it:

::

 moin --help

Creating a wiki instance
========================

You'll need one instance directory per wiki site you want to run using moin -
this is where wiki data, indexes and configuration for that site are stored.

Let's create a new instance:

::

 moin create-instance --path INSTANCE-DIRECTORY

Change into the new instance directory:

::

 cd INSTANCE-DIRECTORY

You'll find a ``wikiconfig.py`` there to edit. Adapt it as you like,
you'll find some comments in there. Review and change the settings
for:

 * sitename
 * interwikiname
 * acls
 * SECRET_KEY

After configuring, you can create an empty wiki by initializing the
storage and the index:

::

 moin index-create -s -i

If you don't want to start with an empty wiki, but rather play with some
sample content we provide, load it into your wiki and rebuild the indexes:

::

 moin load-sample
 moin index-build

 Or, if you have a moin 1.9.x wiki, convert it to moin 2:

 ::

  moin import19 -d <path to 1.9 wiki/data> -s -i

If you want to load English help for editors (replace en with your wiki's preferred language):

::

 moin load-help -n en
 moin load-help -n common

Run your wiki instance
======================
Now try your new wiki using the builtin python-based web server:

::

 moin moin  # visit the URL it shows in the log output

For production, please use a real web server like apache or nginx.

For more information on various wiki admin activities, see `Moin Command Line Interface`.


=============================
Installation (for developers)
=============================

Clone the git repository
========================
If you like to work on the moin2 code, clone the master project repository
or see the option below:

::

 cd <to the parent of your moin repo>
 git clone https://github.com/moinwiki/moin
 cd moin

If you use github, you can also first fork the project repo to your own
user's github repositories and then clone your forked repo to your local
development machine. You can easily publish your own changes and
do pull requests that way. If you do fork the project, then an alternative
to the above command is to clone your fork and add a remote url to the
master::

 git clone https://github.com/<your name>/moin
 cd moin
 git remote add moinwiki https://github.com/moinwiki/moin

Installing
==========
Before you can run moin, you need to install it.

Using your standard user account, run the following command
from the project root directory. Replace <python> in the command
below with the path to a python 3.8+ executable. This is usually
just "python", but may be "python3", "python3.8", "/opt/pypy/bin/pypy"
or even <some-other-path-to-python>:

::

 <python> quickinstall.py

 OR

 <python> quickinstall.py <path-to-venv>

The above will download all dependent packages to the PIP cache,
install the packages in a virtual environment, and compile the translations
(`*.po` files) to binary `*.mo` files. This process may take several minutes.

The default virtual environment directory name is:

 * ../<PROJECT>-venv-<PYTHON>/

where <PROJECT> is the name of the project root directory, and <PYTHON>
is the name of your python interpreter. As noted above, the default
name may be overridden.

Check the output of quickinstall.py to determine whether there were
fatal errors. The output messages will normally state that stdout
and stderr messages were written to a file, a few key success/failure
messages will be extracted and written to the terminal window, and
finally a message to type "m" to display a menu.

If there are failure messages, see the troubleshooting section below.

Activate the virtual environment::

 activate #windows
 . activate  # unix

Typing "./m" (or "m" on Windows) will display a menu similar to:

::

    usage: "./m <target>" where <target> is:

    quickinstall    update virtual environment with required packages
    extras          install packages required for docs and moin development
    docs            create moin html documentation (requires extras)
    interwiki       refresh contrib/interwiki/intermap.txt (version control)
    log <target>    view detailed log generated by <target>, omit to see list

    new-wiki        create empty wiki
    sample          create wiki and load sample data
    restore *       create wiki and restore wiki/backup.moin *option, specify file
    import19 <dir>  import a moin 1.9 wiki/data instance from <dir>

    run *           run built-in wiki server *options (--port 8081)
    backup *        roll 3 prior backups and create new backup *option, specify file
    dump-html *     create a static HTML image of wiki *options, see docs
    index           delete and rebuild indexes

    css             run lessc to update basic theme CSS files
    tests *         run tests, log output (-v -k my_test)
    coding-std      correct scripts that taint the repository with trailing spaces..

    del-all         same as running the 4 del-* commands below
    del-orig        delete all files matching *.orig
    del-pyc         delete all files matching *.pyc
    del-rej         delete all files matching *.rej
    del-wiki        create a backup, then delete all wiki data

While most of the above menu choices may be executed now, new users should
do the following to create a wiki instance and load it with sample data.:

::

 m sample   # in Windows
 ./m sample # in Unix

 If you want to load English help for editors (replace en with your wiki's preferred language):

::

 moin load-help -n en
 moin load-help -n common

Next, run the built-in wiki server:

::

 m run      # in Windows
 ./m run    # in Unix

As the server starts, a few log messages will be output to the
terminal window.  Point your browser to http://127.0.0.1:8080, the
sample Home page will appear and more log messages will be output
to the terminal window. Do a quick test by accessing some of the
demo items and do a modify and save. If all goes well, your installation
is complete. The built-in wiki server may be stopped by typing ctrl-C
in the terminal window.

Next Steps
==========

If you plan on contributing to the moin2 project, there are more
instructions waiting for you under the Development topic.

If you plan on using this wiki as a production wiki,
then before you begin adding or importing data and registering users
review the configuration options. See the sections on configuration for
details. Be sure to edit `wikiconfig.py` and change the settings for::

 * sitename
 * interwikiname
 * acls
 * SECRET_KEY

If you plan on just using moin2 as a desktop wiki (and maybe
help by reporting bugs), then some logical menu choices are::

 * `./m extras` - to install packages required for docs and moin development
 * `./m docs` - to create docs, see User tab, Documentation (local)
 * `./m del-wiki` - get rid of the sample data
 * `./m new-wiki` or `m import19 ...` - no data or moin 1.9 data
 * `./m backup` - backup wiki data as needed or as scheduled

If you installed moin2 by cloning the repository,
then you will likely want to keep your master branch uptodate:

::

  git checkout master
  git pull # if you cloned the moinwiki master repo OR
  git pull moinwiki master # if you cloned your fork and added a remote

After pulling updates, it is best to also rerun the quickinstall process
to install any changes or new releases of the dependent packages:

::

 m quickinstall  # in Windows
 ./m quickinstall # in Unix

Troubleshooting
===============

PyPi down
---------
Now and then, PyPi might be down or unreachable.

There are mirrors b.pypi.python.org, c.pypi.python.org, d.pypi.python.org
you can use in such cases. You just need to tell pip to do so:

::

 # put this into ~/.pip/pip.conf
 [global]
 index-url = http://c.pypi.python.org/simple

Bad Network Connection
----------------------
If you have a poor or limited network connection, you may run into
trouble with the commands issued by the quickinstall.py script.
You may see tracebacks from pip, timeout errors, etc. within the output
of the quickinstall script.

If this is the case, you may try rerunning the "python quickinstall.py"
script multiple times. With each subsequent run, packages that are
all ready cached (view the contents of pip-download-cache) will not
be downloaded again. Hopefully, any temporary download errors will
cease with multiple tries.

Other Issues
------------

If you encounter some other issue not described above, try
researching the unresolved issues in our issue tracker.

If you find a similar issue, please add a note saying you also have the problem
and add any new information that may assist in the problem resolution.

If you cannot find a similar issue please create a new issue.
Or, if you are not sure what to do, join us on IRC at #moin-dev
and describe the problem you have encountered.
