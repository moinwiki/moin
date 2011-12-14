==========================
Downloading and Installing
==========================

Downloading
===========
For moin2, there is currently no packaged download available, so you have to get
it from the repository.
You can use one of two repository URLs (there is little difference between them),
and either use Mercurial to keep a constantly updated copy of the code or download an archive of the files in tar.gz format:

Example using Mercurial with the first URL::

 hg clone http://hg.moinmo.in/moin/2.0 moin-2.0
 hg up -C default  # update workdir to "default" branch

Example using Mercurial with the second URL::

 $ hg clone http://bitbucket.org/thomaswaldmann/moin-2.0 moin-2.0
 hg up -C default  # update workdir to "default" branch

Alternatively, visit http://hg.moinmo.in/moin/2.0 with your web browser and download the archive
(usually for the "default" branch) and unpack it.

Installing
==========
Before you can run moin, you need to install it:

Developer install
-----------------
Using your standard Python install or a virtualenv directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Please make sure you have `virtualenv` installed (it includes `pip`).

Please make sure you have virtualenv installed (it includes pip).
If you just want to run moin in-place in your mercurial working directory
with your normal system installation of Python,
run the following command from your mercurial moin2
working directory (you should not run this as an administrator; use your standard user account)::

 ./quickinstall  # for Linux (or other posix OS's)
 # or
 quickinstall.bat  # for windows

This will use virtualenv to create a directory `env/` within the current directory,
create a virtual environment for MoinMoin and then install moin2 including all dependencies into that directory.
`pip` will automatically fetch all dependencies from PyPI and install them, so this may take a while.
It will also compile the translations (`*.po` files) to binary `*.mo` files.
Please review the output of the quickinstall script, and check whether there were fatal errors.
If you have a bad network connection that makes the downloads fail, you can try to do the steps in quickinstall manually.
Further, the quickinstall script will create a `moin` script for your
platform which you can use for starting the built-in server or invoke moin script commands.
After you activated the virtual environment, the built-in server script (named `moin`) will be in the standard PATH,
so you can just run the command `moin` verbatim on the command line.
Note: in this special mode, it won’t copy the MoinMoin code to the env/ directory,
it will run everything from your work dir, so you can modify code and directly try it out
(you only need to do this installation procedure once).

Using a different Python or a different virtualenv directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the `quickinstall` script and just modify the following lines as needed before
running it::

    DIR=env
    PYTHON=python

For example, if you want to use `PyPy` and want to name the virtualenv directory `env-pypy`,
use::

    DIR=env-pypy
    PYTHON=/opt/pypy/bin/pypy

That way, you can test with different versions of Python in different virtualenv directories within your moin2 workdir.

Entering the virtual env
------------------------
To enter your virtual environment::

 source env/bin/activate  # for linux (or other posix OSes)
 # or
 env\Scripts\activate.bat  # for windows

Initializing index and/or storage
---------------------------------
If you have an existing storage AND a valid index (for this storage’s content, and for this moin version),
you can skip this section.
If you start from scratch (no storage created yet, and no index created yet),
you need to create an (empty) storage and an (empty) index::

 moin index-build -s -i

If you already have an existing storage, but no index yet::

 moin index-build -i

Loading some items
------------------
If you don't want to have a completely empty wiki, you may want to load
some default items into it. We provide some in the `contrib/serialized` directory and you
can load them like this::

 # load some example items:
 moin load --file contrib/serialized/preloaded_items.moin

.. todo::
   Example items file is missing, and we still need to build one.

Installing PIL
~~~~~~~~~~~~~~
For some image processing functions that MoinMoin uses (like resizing, rotating),
you need PIL (Python Imaging Library).

Windows users who want to install PIL should skip the remainder of this section and read
Troubleshooting -- PIL Installation Under Windows below.

If you install PIL with pip, pip will try to find a jpeg support library and associated development
headers on your system and if you do not have that, there will be no jpeg support in PIL.
So, if you want jpeg support, make sure you have the jpeg libs/headers::

 # install jpeg library and development headers:
 sudo apt-get install libjpeg62-dev  # Ubuntu / Debian-based
 yum install libjpeg-turbo-devel  # Fedora / Redhat-based

Now install PIL into your virtual environment::

 # enter your virtual environment:
 source env/bin/activate  # for linux (or other posix OSes)

 # install Python Imaging Library:
 pip install pil # for linux (or other posix OSes)

Troubleshooting
-----------------

Bad Network Connection
~~~~~~~~~~~~~~~
If you have a poor or limited network connection, you may run into trouble with the commands issued by
the quickinstall script.
You may see tracebacks from pip, timeout errors, etc. (see the output of the quickinstall script).

If this is the case, try it manually:
 # enter your virtual environment:
 source env/bin/activate

 # confirm the problems by running:
 pip install -e .

Now install each package into your virtual env manually:

* Find the required packages by looking at "install_requires" within `setup.py`.
* Download each required package from http://pypi.python.org/
* Install each of them individually by::

    pip install package.tar

* Now try again::

    pip install -e .

Repeat these steps until you don't see fatal errors.

PIL Installation Under Windows
~~~~~~~~~~~~~~~~~~~~
PIL version 1.1.7 does not install correctly via "pip install pil" on Windows.
Some users have had success using "pip install pillow" (a fork of PIL fixing
a packaging issue).  Other users have resorted to installing PIL 1.1.6 in the
main Python directory using the Windows installers available at
http://www.pythonware.com/products/pil/
