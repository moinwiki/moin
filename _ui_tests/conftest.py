# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""
Contains events called by pytest during the life-cycle of the test suite
This module is automatically loaded by pytest, which looks for a file
of this name
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))
import driver_register


def pytest_runtest_makereport(item, call):
    """
    Entry point for event which occurs after each test has run
    The parameters are:
    - item: the method called
    - call: an object of type CallInfo, which has two properties, of which
      excinfo contains info about any exception that got thrown by the method
    This method is called automatically by pytest.  The name of the method
    is used by pytest to locate it, and decide when to call it
    This specific method instance is used to take a screenshot whenever a test
    fails, ie whenever the method throws an exception
    """
    if call.excinfo is not None:
        if driver_register.get_driver() is not None and hasattr(item, "obj"):
            driver_register.get_driver().get_screenshot_as_file(str(item.obj).split(" ")[2] + ".png")
