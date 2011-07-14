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
    """ Test: util.pycdb.CDBMaker """
    
    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'test_cdb')
        self.test_tmpname = os.path.join(self.test_dir, "test_tmpfile")
        self.test_cdbname = os.path.join(self.test_dir, "test_cdbfile")
        self.CDBMaker_obj = pycdb.CDBMaker(self.test_cdbname, self.test_tmpname)

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
        
    def test_add(self):
        result = os.listdir(self.test_dir)
        result1 = self.CDBMaker_obj.__len__()
        expected = ['test_tmpfile']
        assert result == expected

        self.CDBMaker_obj = self.CDBMaker_obj.add(' k_value - ', 'v_value')
        self.CDBMaker_obj._fp = open(self.test_tmpname, 'r');
        # seek to 2048 since self._pos was assigned to 2048 initially.
        self.CDBMaker_obj._fp.seek(2048)
        # read the contents i.e. newly added contents
        result = self.CDBMaker_obj._fp.read()
        expected = '\x0b\x00\x00\x00\x07\x00\x00\x00 k_value - v_value'
        assert result == expected
    
    def test_finish(self):
        # add contents to cdb_file
        self.CDBMaker_obj = self.CDBMaker_obj.add(' k_value - ', 'v_value')
        # remove tmpfile
        self.CDBMaker_obj.finish()
        result = os.listdir(self.test_dir)
        expected = ['test_cdbfile']
        assert result == expected

class TestCDBReader:
    """ Test: util.pycdb.CDBReader """

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'test_cdb')
        self.test_tmpname = os.path.join(self.test_dir, "test_tmpfile")
        self.test_cdbname = os.path.join(self.test_dir, "test_cdbfile")
        self.CDBMaker_obj = pycdb.CDBMaker(self.test_cdbname, self.test_tmpname)

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
                
    def test_get(self):
        # add k and v
        self.CDBMaker_obj = self.CDBMaker_obj.add(' k_value - ', 'v_value')
        # remove tmpfile
        self.CDBMaker_obj.finish()
        CDBReader_obj = pycdb.CDBReader(self.test_cdbname)
        result = CDBReader_obj.get(' k_value - ', failed=None)
        expected = 'v_value'
        assert result == expected

        # check for the has_key
        result = CDBReader_obj.has_key(' k_value - ')
        assert result
        # invalid key
        result = CDBReader_obj.has_key('not_present')
        assert not result
