# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""
This module is used to register the webdriver driver module as a global
variable, so that it can be used by conftest methods, eg for doing a
printscreen when a test fails
"""

driver = None


def register_driver(driver_):
    """
    set the driver global variable to driver_
    """
    global driver
    driver = driver_


def get_driver():
    """
    get the value of the driver global variable
    """
    global driver
    return driver
