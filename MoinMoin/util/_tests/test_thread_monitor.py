# -*- coding: utf-8 -*-
# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.thread_monitor Tests
"""

import shutil, tempfile
import os

import pytest
from MoinMoin.util.thread_monitor import Monitor

class TestMonitor(object):
    """ Tests: Monitor """

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp('', 'test_dump')
        self.src = os.path.join(self.test_dir, "test_dumpfile")

    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)

    def test_hook(self):
        """ tests for hooks """
        Monitor_test_obj = Monitor()
        result_inactivated = Monitor_test_obj.hook_enabled()
        assert not result_inactivated
        # activate the hook
        Monitor_test_obj.activate_hook()
        result_activated = Monitor_test_obj.hook_enabled()
        assert result_activated

    def test_trigger_dump(self):
        """ test for trigger_dump """
        Monitor_test_obj = Monitor()
        # activate the hook first
        Monitor_test_obj.activate_hook()
        with open(self.src, "w") as f:
            result = Monitor_test_obj.trigger_dump(f)
        # read the content of first line
        with open(self.src, "r") as f:
            f.seek(1)
            assert 'Dumping thread' in f.readline()
