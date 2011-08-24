# Copyright: 2008 MoinMoin:JohannesBerg
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Test - FSBackend
"""


import py, os, tempfile, shutil

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.fs import FSBackend

class TestFSBackend(BackendTest):

    def create_backend(self):
        self.tempdir = tempfile.mkdtemp('', 'moin-')
        return FSBackend(self.tempdir)

    def kill_backend(self):
        try:
            for root, dirs, files in os.walk(self.tempdir):
                for d in dirs:
                    assert not d.endswith('.lock')
                for f in files:
                    assert not f.endswith('.lock')
                    assert not f.startswith('tmp-')
        finally:
            shutil.rmtree(self.tempdir)

    def test_large(self):
        i = self.backend.create_item(u'large')
        r = i.create_revision(0)
        r[u'0'] = u'x' * 100
        r[u'1'] = u'y' * 200
        r[u'2'] = u'z' * 300
        for x in xrange(1000):
            r.write('lalala! ' * 10)
        i.commit()

        i = self.backend.get_item(u'large')
        r = i.get_revision(0)
        assert r[u'0'] == u'x' * 100
        assert r[u'1'] == u'y' * 200
        assert r[u'2'] == u'z' * 300
        for x in xrange(1000):
            assert r.read(8 * 10) == 'lalala! ' * 10
        assert r.read() == ''

    def test_all_unlocked(self):
        i1 = self.backend.create_item(u'existing now 1')
        i1.create_revision(0)
        i1.commit()
        i2 = self.backend.get_item(u'existing now 1')
        i2.change_metadata()
        # if we leave out the latter line, it fails
        i2.publish_metadata()

