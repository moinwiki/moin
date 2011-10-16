# Copyright: 2006 by Armin Rigo (originally only testing for tab chars)
# Copyright: 2007 adapted and extended (calling the PEP8 checker for most stuff) by MoinMoin:ThomasWaldmann.
# License: MIT licensed

"""
Verify that the MoinMoin source files conform (mostly) to PEP8 coding style.

Additionally, we check that the files have no crlf (Windows style) line endings.
"""


import re, time
import pytest
from . import pep8

import py

moindir = py.path.local(__file__).pypkgpath()

EXCLUDE = set([
    moindir/'static', # this is our dist static stuff
    moindir/'_tests/wiki', # this is our test wiki
])

TRAILING_SPACES = 'nochange' # 'nochange' or 'fix'
                             # use 'fix' with extreme caution and in a separate changeset!
FIX_TS_RE = re.compile(r' +$', re.M) # 'fix' mode: everything matching the trailing space re will be removed

try:
    import xattr
    if not hasattr(xattr, "xattr"): # there seem to be multiple modules with that name
        raise ImportError
    def mark_file_ok(path, mtime):
        x = xattr.xattr(path)
        try:
            x.set('user.moin-pep8-tested-mtime', str(int(mtime)))
        except IOError:
            # probably not supported
            global mark_file_ok
            mark_file_ok = lambda path, mtime: None

    def should_check_file(path, mtime):
        x = xattr.xattr(path)
        try:
            mt = x.get('user.moin-pep8-tested-mtime')
            mt = long(mt)
            return mtime > mt
        except IOError:
            # probably not supported
            global should_check_file
            should_check_file = lambda path, mtime: True
        return True
except ImportError:
    def mark_file_ok(path, mtime):
        pass
    def should_check_file(path, mtime):
        return True

RECENTLY = time.time() - 7 * 24*60*60 # we only check stuff touched recently.
#RECENTLY = 0 # check everything!

# After doing a fresh clone, this procedure is recommended:
# 1. Run the tests once to see if everything is OK (as cloning updates the mtime,
#    it will test every file).
# 2. Before starting to make new changes, use "touch" to change all timestamps
#    to a time before <RECENTLY>.
# 3. Regularly run the tests, they will run much faster now.

def pep8_error_count(path):
    # process_options initializes some data structures and MUST be called before each Checker().check_all()
    pep8.process_options(['pep8', '--ignore=E202,E221,E222,E241,E301,E302,E401,E501,E701,W391,W601,W602', '--show-source', 'dummy_path'])
    error_count = pep8.Checker(path).check_all()
    return error_count

def check_py_file(reldir, path, mtime):
    if TRAILING_SPACES == 'fix':
        f = file(path, 'rb')
        data = f.read()
        f.close()
        fixed = FIX_TS_RE.sub('', data)

        # Don't write files if there's no need for that,
        # as altering timestamps can be annoying with some tools.
        if fixed == data:
            return

        f = file(path, 'wb')
        f.write(fixed)
        f.close()
    # Please read and follow PEP8 - rerun this test until it does not fail any more,
    # any type of error is only reported ONCE (even if there are multiple).
    error_count = pep8_error_count(path)
    assert error_count == 0
    mark_file_ok(path, mtime)

def pytest_generate_tests(metafunc):
    for pyfile in sorted(moindir.visit('*.py', lambda p: p not in EXCLUDE)):
        relpath = moindir.bestrelpath(pyfile)
        metafunc.addcall(id=relpath, funcargs={'path': pyfile})

def test_sourcecode(path):
    mtime = path.stat().mtime
    if mtime < RECENTLY:
        pytest.skip("source change not recent")
    if not should_check_file(str(path), mtime):
        pytest.skip("source marked as should not be checked")

    check_py_file(str(moindir.bestrelpath(path)), str(path), mtime)


