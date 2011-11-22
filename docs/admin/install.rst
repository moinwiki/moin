==========================
Downloading and Installing
==========================

Downloading
===========
For moin2, there is currently no packaged download available, you have to get
it from the repository:

Alternative 1a (using Mercurial DVCS)::

 hg clone http://hg.moinmo.in/moin/2.0 moin-2.0
 hg up -C default  # update workdir to "default" branch

Alternative 1b (using Mercurial DVCS)::

 $ hg clone http://bitbucket.org/thomaswaldmann/moin-2.0 moin-2.0
 hg up -C default  # update workdir to "default" branch

Alternative 2:
Visit http://hg.moinmo.in/moin/2.0 with your web browser, download the tgz
(usually for the "default" branch) and unpack it.

Installing
==========
Before you can run moin, you need to install it:

Developer install
-----------------
Please make sure you have `virtualenv` installed (it includes `pip`).

If you just want to run moin in-place in your mercurial workdir, with your
normal system Python, run this from your mercurial moin2 work dir (you should
do this using your normal user login, no root or Administrator privileges needed)::

 ./quickinstall  # for linux (or other posix OSes)
 # or
 quickinstall.bat  # for windows

This will use virtualenv to create a directory `env/` and create a virtual
environment for moin there and then install moin2 including all dependencies
into that directory.
pip will fetch all dependencies from pypi and install them, so this may take
a while.
It will also compile the translations (`*.po` files) to binary `*.mo` files.

Please review the output of the quickinstall script, whether there were fatal
errors. In case you have a bad network connection that makes the downloads
fail, you can try to do the steps in quickinstall manually.

Further, it will create a "moin" script for your platform which you can use
for starting moin (the builtin server) or invoke moin script commands.
After you activated the virtual environment, the moin script will be in the
PATH, so you can just type "moin" on the shell / cmd.

Note: in this special mode, it won't copy the MoinMoin code to the env/
directory, it will run everything from your work dir, so you can modify code
and directly try it out (you only need to do this installation procedure once).

Using a different Python or a different virtualenv directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the `quickinstall` script and just modify these lines as needed before
running it::

    DIR=env
    PYTHON=python

E.g. if you want to use `pypy` and name the virtualenv directory `env-pypy`,
use::

    DIR=env-pypy
    PYTHON=/opt/pypy/bin/pypy

That way, you can have all sorts of Pythons in different virtualenv directories
within your moin2 workdir.


Entering the virtual env
------------------------
Enter your virtual environment::

 source env/bin/activate

Initializing index and/or storage
---------------------------------
If you start from scratch (no storage created yet, no index created yet),
you need to creates an (empty) storage and an (empty) index::

 moin index-build -s -i

If you already have an existing storage, but no index yet::

 moin index-build -i

If you have an existing storage AND a valid index (for this storage's content,
for this moin version), you can skip this section.

Loading some items
------------------
In case you do not want to have a completely empty wiki, you may want to load
some items into it. We provide some in `contrib/serialized` directory and you
can load them like this::

 # load some example items:
 moin load --file contrib/serialized/preloaded_items.moin

.. todo::
   example items file is missing, build one.

Installing PIL
~~~~~~~~~~~~~~
For some image processing functions (like resizing, rotating) of moin, you
need PIL (Python Imaging Library). If you install it with pip, it'll try to
find some jpeg support library and development headers on your system and
in case you don't have that, there will be no jpeg support in PIL.

So, if you want jpeg support, make sure you have the jpeg libs/headers::

 # install jpeg library and development headers:
 sudo apt-get install libjpeg62-dev  # ubuntu / debian
 yum install libjpeg-turbo-devel  # fedora / red hat

Now install PIL into your virtual environment::

 # enter your virtual environment:
 source env/bin/activate

 # install Python Imaging Library:
 pip install pil

Troubleshooting
~~~~~~~~~~~~~~~
If you have a bad or limited network connection, you may run into trouble
with the commands issued by the quickinstall script.

You may see tracebacks from pip, timeout errors, etc. (see the output of the
quickinstall script).

If this is the case, try it manually::

 # enter your virtual environment:
 source env/bin/activate

 # confirm the problems by running:
 pip install -e .

Now install each package into your virtual env manually:

* Find the required packages by looking into setup.py (see install_requires).
* Download the package from http://pypi.python.org/
* Install each of them individually by::
 
    pip install package.tar

* Now try again::

    pip install -e .

Repeat these steps until you don't see fatal errors any more.

