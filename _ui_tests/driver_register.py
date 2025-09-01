# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""
Register the WebDriver instance as a global so it can be accessed by
conftest hooks, e.g., to take a screenshot when a test fails.
"""

driver = None


def register_driver(driver_):
    """
    Set the global driver variable to driver_.
    """
    global driver
    driver = driver_


def get_driver():
    """
    Get the value of the global driver variable.
    """
    global driver
    return driver
