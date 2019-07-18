"""
Copyright: 2019 MoinMoin:RogerHaase
License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

This Locust test script may be used to identify bugs that may occur
when multiple items are created or updated in rapid succession.

This test requires user self-registration, set wikiconfig configuration to:
    registration_only_by_superuser = False
    user_email_verification = False
    edit_locking_policy = 'lock'
    edit_lock_time = 2  # or any number of minutes

Running this script will register users, create user home pages,
and create wiki items as part of the test. It is best to start with
an empty wiki (./m new-wiki).

To load test Moin2:
 * read about Locust at https://docs.locust.io/en/stable/index.html
 * install Locust per the docs
 * open a terminal window and start the built-in server (./m run)
   * (skip the above if using a remote server)
 * open a terminal window for the locus server
   * if Locust is installed in a virtualenv, activate it
   * cd to this directory (else use the -f option to point to locustfile.py)
   * start Locust, specify host (locust --host=http://127.0.0.1:8080)
 * open a browser and direct it to http://127.0.0.1:8089
   * on Windows 10 you may have to use http://localhost:8089
   * start with 1 user with a hatch rate of 1 per second, increase users on subsequent tests
   * watch for error messages in both terminal windows and the browser
 * click the stop link on the browser to stop the test
 * customize and repeat:
   * ./m del-wiki; ./m new-wiki
    * restart Moin2 buit-in server
    * restart Locust server
    * refresh browser window
"""


import sys
import argparse
import urllib.request, urllib.error, urllib.parse

from locust import HttpLocust, Locust, TaskSet, TaskSequence, task, seq_task


user_number = 0
# test content to put load on indexer
extra_content = """
= %s Home Page =

== Writing a locustfile ==
A locustfile is a normal python file. The only requirement is that it declares at least one class -
let's call it the locust class - that inherits from the class Locust.

=== The Locust class ===
A locust class represents one user (or a swarming locust if you will). Locust will spawn (hatch) one
instance of the locust class for each user that is being simulated. There are a few attributes
that a locust class should typically define.

=== The task_set attribute ===
The task_set attribute should point to a TaskSet class which defines the behaviour of the user and
is described in more detail below.

=== The min_wait and max_wait attributes ===
In addition to the task_set attribute, one usually wants to declare the min_wait and max_wait
attributes. These are the minimum and maximum time respectively, in milliseconds, that a simulated
user will wait between executing each task. min_wait and max_wait default to 1000, and therefore a
locust will always wait 1 second between each task if min_wait and max_wait are not declared.

With the following locustfile, each user would wait between 5 and 15 seconds between tasks:

{{{#!python
from locust import Locust, TaskSet, task

class MyTaskSet(TaskSet):
    @task
    def my_task(self):
        print("executing my_task")

class MyLocust(Locust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
}}}
"""


class UserSequence(TaskSequence):
    """
    Register a new user, login, create a home page, modify home page several times,
    create a new item, modify new item several times, and logout.
    """

    @seq_task(0)
    def get_home(self):
        # Home and users/Home have been created by setup, see below
        response = self.client.get("/Home")
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(1)
    def click_login(self):
        global user_number
        user_number += 1
        self.user_name = 'JohnDoe' + str(user_number)
        self.user_email = self.user_name + '@john.doe'
        self.user_home_page = '/users/' + self.user_name
        print('==== starting user = %s ====' % self.user_name)
        response = self.client.get("/+login")
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(2)
    def click_register(self):
        response = self.client.get("/+register")
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(3)
    def click_post_register(self):
        response = self.client.post("/+register",
                                    {"register_username": self.user_name,
                                     "register_password1": "locust123",
                                     "register_password2": "locust123",
                                     "register_email": self.user_email,
                                    })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(4)
    def click_login_again(self):
        response = self.client.get("/+login")
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(5)
    def click_post_login(self):
        response = self.client.post("/+login",
                                    {"login_username": self.user_name,
                                     "login_password": "locust123",
                                     "login_submit": "1",
                                     "login_nexturl": "/Home",
                                    })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(6)
    def create_home_page(self):
        # click link to users home page (home page has not been created: 404 expected)
        response = self.client.get(self.user_home_page, catch_response=True)
        if response.status_code == 404:
            response.success()
        else:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # click MoinMoin markup link
        home_page_get = '/+modify/users/' + self.user_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default'
        response = self.client.get(home_page_get)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = '= %s =\n\nMy Home Page created by Locust' % self.user_name
        home_page_post = '/+modify/users/' + self.user_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template='
        response = self.client.post(home_page_post,
                                    {"content_form_data_text": new_content,
                                     "comment": "my comment",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "apple, pear",
                                     "meta_form_name": self.user_name,
                                     "extra_meta_text": '{"namespace": "users","rev_number": 1}',
                                     })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(7)
    @task(4)
    def modify_home_page(self):
        # get users home page
        response = self.client.get(self.user_home_page)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # click modify link
        home_page = '/+modify' + self.user_home_page + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template='
        response = self.client.get(home_page)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # update the page
        response = self.client.post(home_page,
                                    {"content_form_data_text": extra_content % self.user_name,
                                     "comment": "my homepage comment",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "apple, pear",
                                     "meta_form_name": self.user_name,
                                     "extra_meta_text": '{"namespace": "users","rev_number":1}',
                                     })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(8)
    def create_new_page(self):
        # first get yields 404 status code
        new_item_name = 'Locust-' + self.user_name
        response = self.client.get('/' + new_item_name, catch_response=True)
        if response.status_code == 404:
            response.success()
        else:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # click MoinMoin markup link
        page_get = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default'
        response = self.client.get(page_get)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = '= %s =\n\nNew Item created by Locust' % new_item_name
        new_page_post = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template='
        response = self.client.post(new_page_post,
                                    {"content_form_data_text": new_content,
                                     "comment": "yes",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "lime, orange",
                                     "meta_form_name": new_item_name,
                                     "extra_meta_text": '{"namespace": "","rev_number": 1}',
                                     })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(9)
    @task(10)
    def modify_new_page(self):
        # click link to new page
        new_item_name = 'Locust-' + self.user_name
        response = self.client.get('/' + new_item_name)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # click MoinMoin markup link
        page_get = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default'
        response = self.client.get(page_get)
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = '= %s =\n\nNew Item created by Locust' % new_item_name
        new_page_post = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template='
        response = self.client.post(new_page_post,
                                    {"content_form_data_text": extra_content,
                                     "comment": "yes",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "lime, orange",
                                     "meta_form_name": new_item_name,
                                     "extra_meta_text": '{"namespace": "","rev_number": 1}',
                                     })
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))

    @seq_task(10)
    def logout(self):
        response = self.client.get("/+logout?logout_submit=1")
        if response.status_code != 200:
            print('%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code))


class WebsiteUser(HttpLocust):

    task_set = UserSequence
    min_wait = 2000
    max_wait = 3000

    def setup(self):
        """create Home and users/Home items"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--host', '-H')
        args, unknown = parser.parse_known_args()
        host = args.host
        if host:
            if host.endswith('/'):
                host = host[:-1]

            print('==== creating Home and users/Home ====')
            url = host + "/+modify/users/Home?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
            data = urllib.parse.urlencode({"content_form_data_text": "= users/Home =\n * created by Locust",
                                     "comment": "",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "None",
                                     "meta_form_name": "Home",
                                     "extra_meta_text": '{"namespace": "users","rev_number": 1}',
                                     })
            content = urllib.request.urlopen(url=url, data=data).read()

            url = host + "/+modify/Home?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
            data = urllib.parse.urlencode({"content_form_data_text": "= Home =\n * created by Locust",
                                     "comment": "",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "None",
                                     "meta_form_name": "Home",
                                     "extra_meta_text": '{"namespace": "","rev_number": 1}',
                                     })
            content = urllib.request.urlopen(url=url, data=data).read()
