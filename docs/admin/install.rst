==========================
Downloading and Installing
==========================

Downloading
===========
For moin2, there is currently no packaged download available, you have to get
it from the repository:

Alternative 1 (using Mercurial DVCS)::

 $ hg clone http://hg.moinmo.in/moin/2.0 moin-2.0

Alternative 2:
Visit http://hg.moinmo.in/moin/2.0 with your web browser, download the tgz
and unpack it.

Installing
==========
Before you can run moin, you need to install it:

Developer install
-----------------
Please make sure you have `virtualenv` installed (it includes `pip`).

If you just want to run moin in-place in your mercurial workdir, run this
from your mercurial moin2 work dir::

 ./quickinstall  # for linux (or other posix OSes)
 # or
 quickinstall.bat  # for windows

This will use virtualenv to create a directory `env/` and create a virtual
environment for moin there and then install moin2 including all dependencies
into that directory.
pip will fetch all dependencies from pypi and install them, so this may take
a while.
It will also compile the translations (`*.po` files) to binary `*.mo` files.

Note: in this special mode, it won't copy moin to the env/ directory, it will
run everything from your work dir, so you can modify code and directly try it
out (you only need to do this installation procedure once).

After successfully installing, you can enter the virtual env and start moin by::

 source env/bin/activate
 ./moin

We activate that virtual environment, so moin will find all its dependencies
and finally start the builtin server using the `moin` script.

