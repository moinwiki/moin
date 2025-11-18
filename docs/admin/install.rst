============
Installation
============

Installing the code
===================
There are a lot of ways to do this and as this is not moin specific,
we won't go into details:

- As long as moin2 is in pre-release stages, this is likely your only and best choice.
  If you use LDAP, you will have to install OS-dependent packages yourself.
  You will have to install Moin updates and security fixes yourself.
  Create a virtual environment first for better separation, then install Moin:

::

  <python3> -m venv </path/to/new/virtual/environment>
  cd </path/to/new/virtual/environment>
  source bin/activate  # or "scripts\activate" on Windows
  pip install --pre moin


- Or, use your operating system's / distribution's package manager to install the
  moin2 package. This is the recommended method as it will install moin2 and
  all other software it requires. Also your OS / dist might have a mechanism
  for updating the installed software with security fixes and future releases.

  For example, on Debian/Ubuntu Linux:

::

  apt install moin

- Or, install into a virtual environment from PyPI.
  You will have to install Moin updates and security fixes yourself:

::

  <python3> -m venv </path/to/new/virtual/environment>
  cd </path/to/new/virtual/environment>
  source bin/activate  # or "scripts\activate" on Windows
  pip install moin


After installation, you should have a ``moin`` command available, try it:

::

 moin --help

If you are running Python 3.12+ and get a traceback with::

 ModuleNotFoundError: No module named 'pkg_resources'

then you must install setuptools manually::

 pip install setuptools

and retry `moin --help`


Creating a wiki instance
========================

You'll need one instance directory per wiki site you want to run using Moin;
this is where wiki data, indexes, and configuration for that site are stored.

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
 * ACLs - SuperUser and SuperEditor
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
Now try your new wiki using the built-in Python-based web server:

::

 moin run  # visit the URL it shows in the log output

For production, please use a real web server like Apache or nginx.

For more information on various wiki admin activities, see `Moin Command Line Interface`.


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
