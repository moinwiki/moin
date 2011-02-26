"""
    MoinMoin - MercurialBackend tests

    Testcases for MercurialBackend based on stable version
    of Mercurial.

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""
from tempfile import mkdtemp, mkstemp, gettempdir
import shutil
import os
import py

try:
    import mercurial
except ImportError:
    py.test.skip('Cannot test without Mercurial installed.')

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError

class TestMercurialBackend(BackendTest):


    def create_backend(self):
        self.test_dir = mkdtemp()
        return MercurialBackend(self.test_dir)

    def kill_backend(self):
        shutil.rmtree(self.test_dir)

    def test_backend_init(self):
        emptydir, file = mkdtemp(), mkstemp()[1]
        nonexisting = os.path.join(gettempdir(), 'to-be-created')
        nonexisting_nested = os.path.join(gettempdir(), 'second-to-be-created/and-also-nested')
        dirstruct = mkdtemp()
        os.mkdir(os.path.join(dirstruct, "meta"))
        os.mkdir(os.path.join(dirstruct, "rev"))
        try:
            assert isinstance(MercurialBackend(nonexisting), MercurialBackend)
            assert isinstance(MercurialBackend(nonexisting_nested), MercurialBackend)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend) # init on existing
            py.test.raises(BackendError, MercurialBackend, file)
            assert isinstance(MercurialBackend(dirstruct), MercurialBackend)
        finally:
            shutil.rmtree(emptydir)
            shutil.rmtree(dirstruct)
            shutil.rmtree(nonexisting)
            os.unlink(file)

    def test_permission(self):
        import sys
        if sys.platform == 'win32':
            py.test.skip("Not much usable test on win32.")
        no_perms = os.path.join("/", "permission-error-dir")
        py.test.raises(BackendError, MercurialBackend, no_perms)

    def test_backend_init_non_empty_datadir(self):
        datadir = mkdtemp()
        os.mkdir(os.path.join(datadir, "meta"))
        os.mkdir(os.path.join(datadir, "rev"))
        try:
            revitem = mkstemp(dir=os.path.join(datadir, "rev"))[1]
            assert isinstance(MercurialBackend(datadir), MercurialBackend)
            os.unlink(revitem)
            metaitem = mkstemp(dir=os.path.join(datadir, "meta"))[1]
            assert isinstance(MercurialBackend(datadir), MercurialBackend)
            os.unlink(metaitem)
        finally:
            shutil.rmtree(datadir)

    def test_large_revision_meta(self):
        item = self.backend.create_item('existing')
        rev = item.create_revision(0)
        for num in xrange(10000):
            revval = "revision metadata value for key %d" % num
            rev["%s" % num] = revval * 10
        item.commit()
        item = self.backend.get_item('existing')
        rev = item.get_revision(-1)
        assert len(dict(rev)) == 10000 + 1 # 'sha1' key is added automatically on commit
        for num in xrange(10000):
            revval = "revision metadata value for key %d" % num
            assert rev["%s" % num] == revval * 10

    def test_data_after_rename(self):
        item = self.backend.create_item('before')
        rev = item.create_revision(0)
        rev.write("aaa")
        item.commit()
        item.rename("after")
        rev = item.create_revision(1)
        rev.write("bbb")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "aaa"
        rev = item.get_revision(1)
        assert rev.read() == "bbb"

    def test_revision_metadata_key_name(self):
        item = self.backend.create_item('metakey')
        rev = item.create_revision(0)
        rev['_meta_'] = "dummy"
        item.commit()
        item = self.backend.get_item('metakey')
        rev = item.get_revision(-1)
        assert rev['_meta_'] == "dummy"

    def test_index_files_in_repository(self):
        item = self.backend.create_item('indexed')
        rev = item.create_revision(0)
        item.commit()
        repo_items = [i for i in self.backend._repo['']]
        assert len(repo_items) == 2
        assert item._id in repo_items
        assert "%s.rev" % (item._id) in repo_items
        rev = item.get_revision(-1)
        rev.destroy()
        repo_items = [i for i in self.backend._repo['']]
        assert len(repo_items) == 3
        assert "%s.rip" % (item._id) in repo_items
        item.destroy()
        repo_items = [i for i in self.backend._repo['']]
        assert len(repo_items) == 1
        assert "%s.rip" % (item._id) in repo_items

