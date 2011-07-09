# -*- coding: utf-8 -*-
# Copyright: 2011 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin.util.thread_monitor Tests
"""

import pytest
from MoinMoin.util.thread_monitor import Monitor

class TestMonitor(object):
    """ Tests: Monitor """

    def test_hook(self):
        """ tests for hooks """
        Monitor_test_obj = Monitor()
        result_inactivated = Monitor_test_obj.hook_enabled()
        assert not result_inactivated
        # activate the hook
        Monitor_test_obj.activate_hook()
        result_activated = Monitor_test_obj.hook_enabled()
        assert result_activated     
        
