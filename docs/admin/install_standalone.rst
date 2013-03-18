================================
Installing a standalone MoinMoin
================================

These are just some additional hints that only apply for standalone
installation, see the standard installation docs for the generic stuff.

Note: currently, you need moin-2.0 repo's "gae" branch::

 hg up -C gae

You do NOT need to:
* run quickinstall or otherwise use virtualenv/pip (as the result of this
  is not useful for standalone operation)

Instead, do this:
* download http://static.moinmo.in/files/moin2-support.tgz
* unpack it into the toplevel directory of the repo workdir (there should
  be a "support" directory on the same level as the "MoinMoin" directory
  after unpacking). These are all the dependencies moin needs for production
  packaged together.

Then try using "moin.py" from the toplevel directory instead of the "moin"
command::

    python moin.py index-create -s -i  # create an index and a storage
    python moin.py                     # run the standalone server

If you are on some POSIX OS (like Linux), this should also work::

    ./moin.py index-create -s -i  # create an index and a storage
    ./moin.py                     # run the standalone server
