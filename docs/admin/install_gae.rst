===============================
Installing on Google App Engine
===============================

These are just some additional hints that only apply for GAE, see the
standard installation docs for the generic stuff.

Note: currently, you need moin-2.0 repo's "gae" branch::

 hg up -C gae

You do NOT need to:
* run quickinstall or otherwise use virtualenv/pip (as the result of this
  is not useful for GAE)
* create an index (will be done automatically)
* create a storage (will be done automatically)

Instead, do this:
* download http://static.moinmo.in/files/moin2-support.tgz
* unpack it into the toplevel directory of the repo workdir (there should
  be a "support" directory on the same level as the "MoinMoin" directory
  after unpacking). These are all the dependencies moin needs for production
  packaged together.

Then, have a look into app.yaml and make sure that "application" is the same
as in your GAE site settings and the env_variables MOINCFG setting is correct.

Then try running the dev_appserver.py from the Google GAE SDK and point it to
the toplevel directory (== your workdir).

If that works, deploy the files using appcfg.py.

Usage of dev_appserver and appcfg is documented in the GAE SDK documentation.


Notes for creating the support directory / archive
==================================================
Usually you can just use the ready-to-use moin2-support.tgz as described above.

But just for the case you have to recreate it (e.g. to update it), here are
some hints:

* make sure you run some POSIX OS (like Linux), Windows is currently not
  supported. You also need "make", "find", "tar" and "gzip" (but usually you
  should have them).
* make sure that you have a virtualenv "env" in the moin workdir (this is
  the default place and name used by the quickinstall script)
* make sure you use Python 2.7.x
* from the repo workdir, run::

    make support

This will create a "support" directory with all the dependencies needed for
running moin. For more infos about how this is done, see the Makefile.

If you want to create the moin2-support.tgz, just run additionally::

    make supporttgz

