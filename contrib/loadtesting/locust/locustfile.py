# Copyright: 2019 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

import sys
import argparse
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from time import time

from locust import HttpLocust, Locust, TaskSet, HttpUser, task, SequentialTaskSet, between, User, events


test_content = """
= %s Home Page %s =

These comments are also used as content when moin items are created; the result is
a small load is placed upon the Whoosh indexer.

The  primary goal of this test is to create a server overload. A server overload will likely take the
form of a LockError in the Whoosh AsyncWriter (/whoosh/writing.py). Each thread attempting
to update the Whoosh index tries to obtain the write lock for a short period of time (~5
seconds). If the lock is not obtained, a LockError exception is raised and the console log
will show a traceback with the message "server overload or corrupt index". The item was
saved but cannot be accessed because it is not in the index - to correct the error,
stop the server, rebuild the indexes, restart the server.

The maximum load that the wiki server can process is established by trial and error.
With the default wait_time of 2-3 seconds running 3 symultaneous users will create a load of about
one transaction per second. Running 30 users could create a load of about 10
transactions per second - but this may be reduced because the wiki server will have slow responses.

This test requires the user self-registration feature, set the wikiconfig.py configuration to:
    registration_only_by_superuser = False
    user_email_verification = False
    edit_locking_policy = "lock"
    edit_lock_time = 20  # or any number of minutes

Running this script will register users, create user home pages,
and create wiki items as part of the test. It is best to start with
an empty wiki (./m new-wiki).

Each locust user registers a new id, creates and updates a home page in the user namespace,
creates and updates a <username> item in the default namespace, and logs-out.

Because each locust user is working on unique items, it does not test edit locking. Use locustfile2.py
to stress test edit locking.

To load test Moin2:
 * read about Locust at https://docs.locust.io/en/stable/index.html - last tested with Locust 2.9.0
 * install Locust per the docs in its own venv
 * open a terminal window and start the Moin built-in server (./m run)
     * (skip the above if using a remote server)
 * open another terminal window for the Locust server
    * Locust is installed in a virtualenv, activate it
    * cd to the directory containing this file (else use the -f option to point to <path to this file>/locustfile.py)
    * start Locust, specify host (locust --host=http://127.0.0.1:8080)
 * open a browser and direct it to http://127.0.0.1:8089
    * on Windows 10 you may have to use http://localhost:8089
    * start with 1 user with a hatch rate of 1 per second, increase users on subsequent tests
    * watch for error messages in the terminal windows and the http://127.0.0.1:8089 browser window
 * click the stop link on the browser to stop the test
 * customize and repeat:
    * ./m del-wiki
    * ./m new-wiki
    * restart Moin2 buit-in server
    * restart Locust server
    * refresh browser window
"""


# used to create unique user IDs
user_number = 0
# min and max wait time in seconds between user transactions, ignored, there is only 1 task
wait_time = between(2, 3)
# sleep time between GET, POST requests in seconds
sleep_time = 0


class LoadTest(HttpUser):
    """
    First, create a Home page in the default and user namespaces.

    Next create a workflow for each locust user that will
    register a new user, login, create a user home page,
    modify user home page several times,
    create a new item, modify new item several times, and logout.
    """

    @events.test_start.add_listener
    def on_test_start(environment, **kwargs):
        """Create Home and users/Home items"""

        parser = argparse.ArgumentParser()
        parser.add_argument("--host", "-H")
        args, unknown = parser.parse_known_args()
        host = args.host
        if host:
            if host.endswith("/"):
                host = host[:-1]

            print("==== creating Home and users/Home ====")
            url = (
                host + "/+modify/users/Home?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
            )
            data = urllib.parse.urlencode(
                {
                    "content_form_data_text": "= users/Home =\n * created by Locust",
                    "comment": "",
                    "submit": "OK",
                    "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                    "meta_form_itemtype": "default",
                    "meta_form_acl": "None",
                    "meta_form_tags": "None",
                    "meta_form_name": "Home",
                    "extra_meta_text": '{"namespace": "users","rev_number": 1}',
                }
            )
            data = data.encode("utf-8")
            content = urllib.request.urlopen(url=url, data=data).read()

            url = host + "/+modify/Home?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
            data = urllib.parse.urlencode(
                {
                    "content_form_data_text": "= Home =\n * created by Locust",
                    "comment": "",
                    "submit": "OK",
                    "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                    "meta_form_itemtype": "default",
                    "meta_form_acl": "None",
                    "meta_form_tags": "None",
                    "meta_form_name": "Home",
                    "extra_meta_text": '{"namespace": "","rev_number": 1}',
                }
            )
            data = data.encode("utf-8")
            content = urllib.request.urlopen(url=url, data=data).read()

    @task(1)
    def user_workflow(self):
        """Define workflow for each locust"""
        self.get_home()
        self.click_login()
        self.click_post_register()
        self.click_login_again()
        self.click_post_login()
        self.create_home_page()
        for idx in range(10):
            self.modify_home_page(idx)
        self.create_new_page()
        for idx in range(10):
            self.modify_new_page(idx)
        self.logout()

    def get_home(self):
        # Home and users/Home have been created by setup
        with self.client.get("/Home", catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def click_login(self):
        global user_number
        user_number += 1
        self.user_name = "JohnDoe" + str(user_number)
        self.user_email = self.user_name + "@john.doe"
        self.user_home_page = "/users/" + self.user_name
        print("==== starting user = %s ====" % self.user_name)
        with self.client.get("/+login", catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def click_register(self):
        with self.client.get("/+register", catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def click_post_register(self):
        with self.client.post(
            "/+register",
            {
                "register_username": self.user_name,
                "register_password1": "locust123",
                "register_password2": "locust123",
                "register_email": self.user_email,
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def click_login_again(self):
        with self.client.get("/+login", catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def click_post_login(self):
        with self.client.post(
            "/+login",
            {
                "login_username": self.user_name,
                "login_password": "locust123",
                "login_submit": "1",
                "login_nexturl": "/Home",
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def create_home_page(self):
        # click link to users home page (home page has not been created: 404 expected)
        with self.client.get(self.user_home_page, catch_response=True) as response:
            if response.status_code == 404:
                response.success()
            else:
                print(
                    "%s: Starting wiki not empty, user's home page already exists: response.status_code = %s"
                    % (sys._getframe().f_lineno, response.status_code)
                )
        # click MoinMoin markup link
        home_page_get = (
            "/+modify/users/" + self.user_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default"
        )
        with self.client.get(home_page_get, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = "= %s =\n\nMy Home Page created by Locust" % self.user_name
        home_page_post = (
            "/+modify/users/"
            + self.user_name
            + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
        )
        with self.client.post(
            home_page_post,
            {
                "content_form_data_text": new_content,
                "comment": "my comment",
                "submit": "OK",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "apple, pear",
                "meta_form_name": self.user_name,
                "extra_meta_text": '{"namespace": "users","rev_number": 1}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def modify_home_page(self, idx):
        # get users home page
        with self.client.get(self.user_home_page, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # click modify link
        home_page = (
            "/+modify"
            + self.user_home_page
            + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
        )
        with self.client.get(home_page, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # update the page
        with self.client.post(
            home_page,
            {
                "content_form_data_text": test_content % (self.user_name, self.get_time() + " idx=%s" % idx),
                "comment": "my homepage comment",
                "submit": "OK",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "apple, pear",
                "meta_form_name": self.user_name,
                "extra_meta_text": '{"namespace": "users","rev_number":1}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def create_new_page(self):
        # first get yields 404 status code
        new_item_name = "Locust-" + self.user_name
        with self.client.get("/" + new_item_name, catch_response=True) as response:
            if response.status_code == 404:
                response.success()
            else:
                print(
                    "%s: Item already exists, starting wiki not empty: response.status_code = %s"
                    % (sys._getframe().f_lineno, response.status_code)
                )
        # click MoinMoin markup link
        page_get = "/+modify/" + new_item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default"
        with self.client.get(page_get, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = "= %s =\n\nNew Item created by Locust" % new_item_name
        new_page_post = (
            "/+modify/" + new_item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
        )
        with self.client.post(
            new_page_post,
            {
                "content_form_data_text": new_content,
                "comment": "yes",
                "submit": "OK",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "lime, orange",
                "meta_form_name": new_item_name,
                "extra_meta_text": '{"namespace": "","rev_number": 1}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def modify_new_page(self, idx):
        # click link to new page
        new_item_name = "Locust-" + self.user_name
        with self.client.get("/" + new_item_name, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # click MoinMoin markup link
        page_get = "/+modify/" + new_item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default"
        with self.client.get(page_get, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        # complete form and post
        new_content = "= %s =\n\nNew Item created by Locust" % new_item_name
        new_page_post = (
            "/+modify/" + new_item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
        )
        with self.client.post(
            new_page_post,
            {
                "content_form_data_text": test_content % (self.user_name, self.get_time() + " idx=%s" % idx),
                "comment": "yes",
                "submit": "OK",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "lime, orange",
                "meta_form_name": new_item_name,
                "extra_meta_text": '{"namespace": "","rev_number": 1}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def logout(self):
        with self.client.get("/+logout?logout_submit=1", catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def get_time(self):
        return datetime.fromtimestamp(time(), tz=timezone.utc).isoformat()[:19].replace("T", " ")
