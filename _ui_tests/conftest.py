# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""
Pytest hook definitions used during the lifecycle of the test suite.

This module is automatically loaded by pytest, which looks for a file
with this name.
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))
import driver_register


def pytest_runtest_makereport(item, call):
    """
    Entry point for the event that occurs after each test has run.

    Parameters:
    - item: the test function being executed
    - call: a CallInfo object; its excinfo attribute contains information about
      any exception raised by the test

    This function is called automatically by pytest. The function name is used
    by pytest to locate it and to decide when to call it.

    This hook is used to take a screenshot whenever a test fails, i.e., whenever
    the test raises an exception.
    """
    if call.excinfo is not None:
        if driver_register.get_driver() is not None and hasattr(item, "obj"):
            driver_register.get_driver().get_screenshot_as_file(str(item.obj).split(" ")[2] + ".png")
