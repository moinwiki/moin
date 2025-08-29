# Copyright: 2012 MoinMoin:LiHaiyan
# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""Functions to facilitate functional testing."""

import random
import urllib.request, urllib.parse, urllib.error

import pytest

pytest.importorskip("selenium")
webdriver = selenium.webdriver  # noqa

import config

try:
    f = urllib.request.urlopen(config.BASE_URL)
except OSError:
    pytestmark = pytest.mark.skip("The UI tests need a wiki server running on %s" % config.BASE_URL)

import driver_register


def create_browser():
    """
    Instantiate a Firefox browser object, configure it for English,
    register it for screenshots, and set the timeout.
    """
    profile = webdriver.FirefoxProfile()
    profile.set_preference("intl.accept_languages", "en")
    driver = webdriver.Firefox(firefox_profile=profile)
    driver_register.register_driver(driver)  # Register with driver_register so that
    # taking a screenshot on test failure works.
    driver.implicitly_wait(20)
    return driver


def generate_random_word(length):
    """
    Generate a random numeric string of length 'length'.
    """
    word = str(random.randint(10 ** (length - 1), 10**length))
    return word


def generate_random_name(prefix, totallength):
    """
    Create a random name starting with 'prefix',
    with a total length of 'totallength'.
    """
    length = totallength - len(prefix)
    numberword = generate_random_word(length)
    name = prefix + numberword
    return name
