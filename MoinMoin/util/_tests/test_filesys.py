# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - MoinMoin.util.filesys Tests
"""

import sys, os, time
import shutil, tempfile

import pytest

from MoinMoin.util import filesys

win32_only = pytest.mark.skipif("sys.platform != 'win32'")
win32_incompatible = pytest.mark.skipif("sys.platform == 'win32'")

class TestFuid(object):
    """ test filesys.fuid (a better mtime() alternative for up-to-date checking) """

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'fuid_')
        self.fname = os.path.join(self.test_dir, "fuid-test")
        self.tmpname = os.path.join(self.test_dir, "fuid-temp")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)

    def testNoFile(self):
        # no file created
        uid = filesys.fuid(self.fname)

        assert uid is None  # there is no file yet, fuid will fail internally and return None

    def makefile(self, fname, content):
        f = open(fname, "w")
        f.write(content)
        f.close()

    def testNewFile(self):
        # freshly created file
        self.makefile(self.fname, "foo")
        uid1 = filesys.fuid(self.fname)

        assert uid1 is not None  # None would mean some failure in fuid()

    def testUpdateFileInPlace(self):
        # update file in place, changing size and maybe mtime
        self.makefile(self.fname, "foo")
        uid1 = filesys.fuid(self.fname)

        self.makefile(self.fname, "foofoo")
        uid2 = filesys.fuid(self.fname)

        assert uid2 != uid1 # we changed size and maybe mtime

    @win32_incompatible
    def testUpdateFileMovingFromTemp(self):
        # update file by moving another file over it
        # changing inode, maybe mtime, but not size

        self.makefile(self.fname, "foo")
        uid1 = filesys.fuid(self.fname)

        self.makefile(self.tmpname, "bar")
        os.rename(self.tmpname, self.fname)
        uid2 = filesys.fuid(self.fname)

        assert uid2 != uid1 # we didn't change size, but inode and maybe mtime

    @win32_only
    def testStale(self):
        # is a file with mtime older than max_staleness considered stale?

        self.makefile(self.fname, "foo")
        uid1 = filesys.fuid(self.fname)

        time.sleep(2) # thanks for waiting :)
        uid2 = filesys.fuid(self.fname, max_staleness=1)
        assert uid2 != uid1  # should be considered stale if platform has no inode support


class TestRename(object):
    """ test filesys.rename* """

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'rename_')
        self.src = os.path.join(self.test_dir, "rename-src")
        self.dst = os.path.join(self.test_dir, "rename-dst")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)

    def makefile(self, fname, content):
        f = open(fname, "w")
        f.write(content)
        f.close()

    def test_posix_rename_exists(self):
        self.makefile(self.src, "src")
        self.makefile(self.dst, "dst")
        # posix rename overwrites an existing destination
        # (on win32, we emulate this behaviour)
        filesys.rename(self.src, self.dst)
        dst_contents = open(self.dst).read()
        assert dst_contents == "src"

    def test_win32_rename_exists(self):
        self.makefile(self.src, "src")
        self.makefile(self.dst, "dst")
        # win32-like rename does not overwrite an existing destination
        # (on posix, we emulate this behaviour)
        pytest.raises(OSError, filesys.rename_no_overwrite, self.src, self.dst)

    def test_special_rename_exists(self):
        self.makefile(self.src, "src")
        self.makefile(self.dst, "dst")
        pytest.raises(OSError, filesys.rename_no_overwrite, self.src, self.dst, delete_old=True)
        assert not os.path.exists(self.src)

    def test_posix_rename_notexists(self):
        self.makefile(self.src, "src")
        filesys.rename(self.src, self.dst)
        dst_contents = open(self.dst).read()
        assert dst_contents == "src"

    def test_win32_rename_notexists(self):
        self.makefile(self.src, "src")
        filesys.rename_no_overwrite(self.src, self.dst)
        dst_contents = open(self.dst).read()
        assert dst_contents == "src"

    def test_special_rename_notexists(self):
        self.makefile(self.src, "src")
        filesys.rename_no_overwrite(self.src, self.dst, delete_old=True)
        assert not os.path.exists(self.src)


class TestCopy(object):
    """test filesys.copytree"""

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'copytree1')
        self.src1 = os.path.join(self.test_dir, "copytree-src1")
        self.src2 = os.path.join(self.test_dir, "copytree-src2")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.test_dest_dir)

    def makefile(self, src, content):
        f = open(src, "w")
        f.write(content)
        f.close()

    def test_copytree(self):
        self.makefile(self.src1, 'src1')
        self.makefile(self.src2, 'src2')
        self.test_dest_dir = self.test_dir + '_copy'
        filesys.copytree(self.test_dir, self.test_dest_dir)
        # check for the dir contents
        assert sorted(os.listdir(self.test_dir)) == sorted(os.listdir(self.test_dest_dir))

    def test_dir_exist(self):
        """ raise Error if dir already exist """
        self.test_dest_dir = tempfile.mkdtemp('', 'temp_dir')
        with pytest.raises(OSError):
            filesys.copytree(self.test_dir, self.test_dest_dir)

coverage_modules = ['MoinMoin.util.filesys']
