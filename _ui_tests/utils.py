# Copyright: 2012 MoinMoin:LiHaiyan
# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""Functions to facilitate functional testing"""

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
    Instantiates a firefox browser object, and configures it for English language
    and registers it for screenshots, and sets the timeout
    """
    profile = webdriver.FirefoxProfile()
    profile.set_preference("intl.accept_languages", "en")
    driver = webdriver.Firefox(firefox_profile=profile)
    driver_register.register_driver(driver)  # register with
    # driver_register, which is needed so that printscreen on test
    # failure works
    driver.implicitly_wait(20)
    return driver


def generate_random_word(length):
    """
    generates a random string containing numbers, of length 'length'
    """
    word = str(random.randint(10 ** (length - 1), 10**length))
    return word


def generate_random_name(prefix, totallength):
    """
    create a random name, starting with 'prefix'
    of total length 'totallength'
    """
    length = totallength - len(prefix)
    numberword = generate_random_word(length)
    name = prefix + numberword
    return name
