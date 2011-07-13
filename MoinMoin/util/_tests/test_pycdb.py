# -*- coding: utf-8 -*-
# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.pycdb Tests
"""

import os
import shutil, tempfile

import pytest
from MoinMoin.util import pycdb

class TestCDBMaker:
    """ Test: util.CDBMaker """
    
    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'test_cdb')
        self.src = os.path.join(self.test_dir, "cbd_file")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
        
    def test_add(self):
        TestCDBMaker_obj = pycdb.CDBMaker('Moin_test', self.src)
        result = os.listdir(self.test_dir)
        result1 = TestCDBMaker_obj.__len__()
        expected = ['cbd_file']
        assert result == expected

