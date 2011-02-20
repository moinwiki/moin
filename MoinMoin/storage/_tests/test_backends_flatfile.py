# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - FlatFileBackend

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

py.test.skip("BackendTest base class tests quite some stuff that this very simple backend does not provide")
# e.g.: revisioning, extremely long item names, metadata support
# TODO: either fix base class so that it is more useful even to test simple backends,
#       or implement some specific, more simple tests here.

import tempfile, shutil

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.flatfile import FlatFileBackend

class TestFlatFileBackend(BackendTest):

    def create_backend(self):
        self.tempdir = tempfile.mkdtemp('', 'moin-')
        return FlatFileBackend(self.tempdir)

    def kill_backend(self):
        shutil.rmtree(self.tempdir)

