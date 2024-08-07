============
Installation
============

Installing the code
===================
There are a lot of ways to do this and as this is not moin specific,
we won't go into details:

- As long as moin2 is in pre-release stages, this is likely your only and best choice.
  If you use ldap, you will have to install OS dependant packages yourself.
  You will have to install moin updates and security fixes your self.
  Create a virtual env first for better separation, then install moin:

::

  <python3> -m venv </path/to/new/virtual/environment>
  cd </path/to/new/virtual/environment>
  source bin/activate  # or "scripts\activate" on windows
  pip install --pre  moin


- Or, use your operating system's / distribution's package manager to install the
  moin2 package. This is the recommended method as it will install moin2 and
  all other software it requires. Also your OS / dist might have a mechanism
  for updating the installed software with security fixes and future releases.

  E.g. on Debian/Ubuntu Linux

::

  apt install moin

- Or, install into a virtual env from PyPI.
  You will have to install moin updates and security fixes your self.:

::

  <python3> -m venv </path/to/new/virtual/environment>
  cd </path/to/new/virtual/environment>
  source bin/activate  # or "scripts\activate" on windows
  pip install moin



After installation, you should have a ``moin`` command available, try it:

::

 moin --help

If you are running Python 3.12.+ and get a traceback with::

 ModuleNotFoundError: No module named 'pkg_resources'

then you must install setuptools manually::

 pip install setuptools

and retry `moin --help`


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
you'll find some comments in there. Review and change the settings for::

 * sitename
 * interwikiname
 * acls - SuperUser and SuperEditor
 * registration only by superuser
 * edit locking policy
 * email configuration
 * namespaces and backends
 * SECRET_KEY
 * etc.

After configuring, you can create an empty wiki by initializing the
storage and the index:

::

 moin index-create

If you don't want to start with an empty wiki, you can load the welcome
page 'Home' and the English help for editors:

::

 moin welcome
 moin load-help -n help-en
 moin load-help -n help-common

Or, if you have a moin 1.9.x wiki, convert it to moin 2:

::

  moin import19 -d <path to 1.9 wiki/data>


Run your wiki instance
======================
Now try your new wiki using the builtin python-based web server:

::

 moin run  # visit the URL it shows in the log output

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
below with the path to a python 3.9+ executable. This is usually
just "python", but may be "python3", "python3.9", "/opt/pypy/bin/pypy"
or even <some-other-path-to-python>:

::

 <python> quickinstall.py

 OR

 <python> quickinstall.py <path-to-venv>

The above will download all dependent packages to the PIP cache,
install the packages in a virtual environment, and compile the translations
(`*.po` files) to binary `*.mo` files. This process may take several minutes.

The default virtual environment directory name is:

::

 ../<PROJECT>-venv-<PYTHON>/

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

 activate    # in Windows
 . activate  # in Unix or Linux

Typing "./m" (or "m" on Windows) will display a menu similar to:

::

    Usage: "./m <target>" where <target> is:

    quickinstall    update virtual environment with required packages
    extras          install packages required for docs and moin development
    docs            create moin html documentation (requires extras)
    interwiki       refresh contrib/interwiki/intermap.txt (version control)
    log <target>    view detailed log generated by <target>, omit to see list

    new-wiki        create empty wiki
    restore *       create wiki and restore wiki/backup.moin *option, specify file

    backup *        roll 3 prior backups and create new backup *option, specify file
    dump-html *     create a static HTML image of wiki *options, see docs

    css             run lessc to update basic theme CSS files
    tests *         run tests, log output (-v -k my_test)
    coding-std      correct scripts that taint the repository with trailing spaces..

    del-all         same as running the 4 del-* commands below
    del-orig        delete all files matching *.orig
    del-pyc         delete all files matching *.pyc
    del-rej         delete all files matching *.rej
    del-wiki        create a backup, then delete all wiki data

    Please refer to 'moin help' to learn more about the CLI for wiki administrators.

While most of the above menu choices may be executed now, new users should
do the following to create a wiki instance and load it with the English help
for editors and some welcome pages (Home):

::

 moin create-instance --full

Next, run the built-in wiki server:

::

 moin run

As the server starts, a few log messages will be output to the
terminal window.  Point your browser to http://127.0.0.1:5000, the
welcome page will appear and more log messages will be output
to the terminal window. Do a quick test by accessing some of the
help items and do a modify and save. If all goes well, your installation
is complete. The built-in wiki server may be stopped by typing ctrl-C
in the terminal window.

Next Steps
==========

If you plan on contributing to the moin2 project, there are more
instructions waiting for you under the Development topic.

If you plan on using this wiki as a production wiki,
then before you begin adding or importing data and registering users
review the configuration options. See the sections on configuration for
details. Be sure to edit ``wikiconfig.py`` and change the settings for::

 * sitename
 * interwikiname
 * acls
 * SECRET_KEY

If you plan on just using moin2 as a desktop wiki (and maybe
help by reporting bugs), then some logical menu choices are::

 ./m extras       # install packages required for docs and moin development
 ./m docs         # create docs, see User tab, Documentation (local)
 ./m del-wiki     # remove the wiki data from previous tests
 ./m new-wiki     # create empty wiki or
 ./m backup       # backup wiki data as needed or as scheduled

If you installed moin2 by cloning the repository,
then you will likely want to keep your master branch up-to-date:

::

  git checkout master
  git pull                 # if you cloned the moinwiki master repo OR
  git pull moinwiki master # if you cloned your fork and added a remote

Also check to see if there are changes to /src/moin/config/wikiconfig.py
by comparing a diff to the wikiconfig.py in the wiki root.

After pulling updates and updating wikiconfig.py, rerun the quickinstall
process to install any new releases of dependent packages:

::

 m quickinstall   # in Windows
 ./m quickinstall # in Unix or Linux

Verifying signed releases
=========================

Releases are signed with an GPG key and a .asc file is provided for each release.

To verify a signature, the public key needs to be known to GPG.
There are two moin project co-owners, their public keys may be imported into the
local keystore from a keyserver with the fingerprints::

  gpg --recv-keys "6D5B EF9A DD20 7580 5747 B70F 9F88 FB52 FAF7 B393"
  gpg --recv-keys "7AFC F58F A118 9DED 2E86 3C41 3D96 89A8 79BD D615"

If GPG successfully imported the key, the output should include (among other things)::

  gpg: Total number processed: 1

To verify the signature of the moin release, download these files from
https://github.com/moinwiki/moin/releases::

  moin-2.*.*.tar.gz
  moin-2.*.*.tar.gz.asc

Then run::

  gpg --verify moin-2.*.*.tar.gz.asc

With a success, the output should look similar to this::

  gpg: assuming signed data in 'dist/moin-2.0.0a1.tar.gz'
  gpg: Signature made Wed Mar 27 13:54:41 2024 USMST
  gpg:                using RSA key 7AFCF58FA1189DED2E863C413D9689A879BDD615
  gpg: Good signature from "RogerHaase (2024-03-11) <haaserd@gmail.com>" [ultimate]

Troubleshooting
===============

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
