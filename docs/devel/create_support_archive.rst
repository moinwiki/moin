Creating the support directory / archive
========================================

The support directory / archive contains all of MoinMoin's dependencies for
installation scenarios where using virtualenv / pip / setup.py is not possible
or not wanted.

Usually you can just use the ready-to-use moin2-support.tgz as described in
the GAE / standalone installation instructions.

But in case you have to recreate it (e.g. to update it), here are some hints:

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

To create the moin2-support.tgz, just run additionally::

    make supporttgz

