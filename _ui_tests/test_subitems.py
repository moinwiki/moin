# Copyright: 2012 MoinMoin:HughPerkins
# License: GNU GPL v3 (or any later version), see LICENSE.txt for details.

"""Functional test: create subitem"""
import config
import utils


class TestSubitems(object):
    """Functional test: create subitem"""

    def setup_class(self):
        """opens browser and creates some random item names for these tests"""
        self.driver = utils.create_browser()
        self.base_url = config.BASE_URL
        self.base_item_name = u"page_" + utils.generate_random_word(5)
        self.subitem_name = u"subitem_" + utils.generate_random_word(5)

    def create_wiki_item(self, item_name):
        """Creates a new wiki item with name 'item_name'"""
        driver = self.driver

        driver.get(self.base_url + u"/" + item_name)
        driver.find_element_by_link_text(u"Default").click()
        driver.find_element_by_link_text(u"Wiki (MoinMoin)").click()
        driver.find_element_by_link_text(
            u"create the item from scratch").click()
        driver.find_element_by_id("f_content_form_data_text").send_keys(
            u"This is a test item\n")
        driver.find_element_by_id("f_submit").click()

    def test_createsubitem(self):
        """Test create subitem"""
        driver = self.driver

        self.create_wiki_item(self.base_item_name)

        driver.get(self.base_url + u"/" + self.base_item_name)
        driver.find_element_by_link_text(u"Modify").click()
        driver.find_element_by_id(u"f_content_form_data_text").send_keys(
            u"\n[[/" + self.subitem_name + "]]\n")
        driver.find_element_by_id(u"f_submit").click()
        driver.find_element_by_link_text(u"/" + self.subitem_name).click()
        driver.find_element_by_link_text(u"Default").click()
        driver.find_element_by_link_text(u"Wiki (MoinMoin)").click()
        driver.find_element_by_link_text(u"create the item from scratch").click()
        driver.find_element_by_id(u"f_content_form_data_text").send_keys(
            u"This is a test subitem")
        driver.find_element_by_id(u"f_submit").click()
        assert u"This is a test subitem" in driver.find_element_by_id(
            u"moin-content-data").text
        assert driver.title.split(u" - ")[0] == self.base_item_name + \
            u"/" + self.subitem_name

    def teardown_class(self):
        """shuts down browser"""
        self.driver.quit()

if __name__ == u'__main__':
    # This lets us run the test directly, without using py.test
    # This is useful for example for being able to call help, eg
    # 'help(driver)', or 'help(driver.find_element_by_id("f_submit"))'
    testSubitems = TestSubitems()
    testSubitems.setup_class()
    testSubitems.test_createsubitem()
    testSubitems.teardown_class()
