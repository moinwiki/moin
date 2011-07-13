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
        self.src = os.path.join(self.test_dir, "cdb_file")
        self.CDBMaker_obj = pycdb.CDBMaker('Moin_test', self.src)

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
        
    def test_add(self):
        result = os.listdir(self.test_dir)
        result1 = self.CDBMaker_obj.__len__()
        expected = ['cdb_file']
        assert result == expected

        self.CDBMaker_obj = self.CDBMaker_obj.add(' k_value &', ' v_value')
        self.CDBMaker_obj._fp = open(self.src, 'r');
        # seek to 2048 since self._pos was assigned to 2048 initially.
        self.CDBMaker_obj._fp.seek(2048)
        # read the contents i.e. newly added contents
        result = self.CDBMaker_obj._fp.read()
        expected = '\n\x00\x00\x00\x08\x00\x00\x00 k_value & v_value'
        assert result == expected
    
    def test_finish(self):
        # add contents to cdb_file
        self.CDBMaker_obj = self.CDBMaker_obj.add(' k_value &', ' v_value')
        # remove the file
        self.CDBMaker_obj.finish()
        result = os.listdir(self.test_dir)
        expected = []
        assert result == expected

