"""
Copyright: 2019 MoinMoin:RogerHaase
License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

This Locust test script may be used to identify bugs that may occur
when an item is updated by multiple users in rapid succession.

This test requires user self-registration, set wikiconfig configuration to:
    registration_only_by_superuser = False
    user_email_verification = False
    edit_locking_policy = "lock"
    edit_lock_time = 20  # or any number of minutes

Running this script will register users,
and each user will try to update the Home item 10 times. It is best to start with
an empty wiki (./m new-wiki).

If the Home item is
locked by another user, a fail message is created and saved for the next update
attempt. If the Home item is available for update, all fail messages and a success
message are appended to the Home item. If the update for a locust fails on the 10th
attempt, then a new <username> item is created and any remaining fail
messages are written to the item.

To load test Moin2:
 * read about Locust at https://docs.locust.io/en/stable/index.html - last tested with Locust 2.9.0
 * install Locust per the docs in its own venv
 * open a terminal window and start the Moin built-in server (./m run)
     * (skip the above if using a remote server)
 * open another terminal window for the Locust server
    * Locust is installed in a virtualenv, activate it
    * cd to the directory containing this file (else use the -f option to point to <full path to this file>/locustfile2.py)
    * start Locust, specify host and file (locust --host=http://127.0.0.1:8080 -f locustfile2.py)
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

import sys
import argparse
import urllib.request, urllib.parse, urllib.error
import datetime
import time

from locust import HttpLocust, Locust, TaskSet, HttpUser, task, SequentialTaskSet, between, User, events


# used to create unique user IDs
user_number = 0
# min and max wait time in seconds between user transactions, ignored, there is only 1 task
wait_time = between(2, 3)
# sleep time between GET, POST requests in seconds
sleep_time = 0


def get_textarea(html):
    """Return contents of textarea where html is html output from +modify"""
    try:
        html_ = html.split("<textarea ")[1]
        html_ = html_.split(">")[1]
        html_ = html_.split("</textarea>")[0][:-10]
    except IndexError:
        html_ = "Error: malformed html = " + html
    return html_


def format_date_time(dt=None):
    """Return current or passed (dt) time in a human readable format."""
    if dt is None:
        dt = datetime.datetime.now()
    fmt = "%Y-%m-%d %H:%M:%S"
    dt = dt.strftime(fmt)
    return dt


class LoadTest(HttpUser):
    """
    On start, create the Home page. Register a new user, login, modify the Home page several times, and logout.
    """

    @events.test_start.add_listener
    def on_test_start(environment, **kwargs):
        """create Home item"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--host", "-H")
        args, unknown = parser.parse_known_args()
        host = args.host
        if host:
            if host.endswith("/"):
                host = host[:-1]
            print("==== creating Home item ====")
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
        time.sleep(sleep_time)
        self.click_login()
        time.sleep(sleep_time)
        self.click_register()
        time.sleep(sleep_time)
        self.click_post_register()
        time.sleep(sleep_time)
        self.click_login_again()
        time.sleep(sleep_time)
        self.click_post_login()
        time.sleep(sleep_time)
        for idx in range(10):
            self.update_home_page(idx)
            time.sleep(sleep_time)
        self.save_messages()
        time.sleep(sleep_time)
        self.logout()

    def get_home(self):
        self.count = 0
        self.message = ""
        # Home and users/Home have been created by setup, see below
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

    def update_home_page(self, idx):
        """
        Read Home page, modify, preview, save.
        """
        self.count += 1
        dt = format_date_time()
        # click link to Home
        item_name = "Home"
        with self.client.get("/" + item_name, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
        time.sleep(sleep_time)
        # click modify link
        page_get = "/+modify/" + item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default"
        time.sleep(sleep_time)
        with self.client.get(page_get, catch_response=True) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
            if b"is locked by" in response.content:
                # someone else has item locked for editing
                self.message += "\n\n%s Item %s is locked, Locust user %s cannot do change number %s" % (
                    dt,
                    item_name,
                    self.user_name,
                    self.count,
                )
                return
        time.sleep(sleep_time)
        content = response.content.decode("utf-8")
        # add queued failure messages to Home content
        textarea_data = get_textarea(content) + self.message
        self.message = ""
        # complete form and post
        new_content = "%s\n\n%s Item %s updated by Locust user %s change number = %s" % (
            textarea_data,
            dt,
            item_name,
            self.user_name,
            self.count,
        )
        new_page_post = (
            "/+modify/" + item_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
        )

        # do preview
        with self.client.post(
            new_page_post,
            {
                "content_form_data_text": new_content,
                "comment": "my comment",
                "preview": "Preview",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "lime, orange",
                "meta_form_name": item_name,
                "extra_meta_text": '{"namespace": ""}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
            if b"Deletions are marked like this." not in response.content:
                print(
                    "%s: response.status_code = %s --- Missing Deletions are marked like this."
                    % (sys._getframe().f_lineno, response.status_code)
                )
        time.sleep(sleep_time)
        # do save
        with self.client.post(
            new_page_post,
            {
                "content_form_data_text": new_content,
                "comment": "my comment",
                "submit": "OK",
                "meta_form_contenttype": "text/x.moin.wiki;charset=utf-8",
                "meta_form_itemtype": "default",
                "meta_form_acl": "None",
                "meta_form_tags": "lime, orange",
                "meta_form_name": item_name,
                "extra_meta_text": '{"namespace": ""}',
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))

    def save_messages(self):
        """
        If this user was unable to update the Home page on the last try, there will be saved messages.
        Create an item with this users name and add the remaining messages.
        """
        if self.message:
            with self.client.get(
                "/+modify/" + self.user_name + "?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    print("%s: response.status_code = %s" % (sys._getframe().f_lineno, response.status_code))
            # complete form and post
            new_content = "= %s =\n\n== Unsaved locked out messages ==%s" % (self.user_name, self.message)
            home_page_post = (
                "/+modify/"
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
                    "meta_form_tags": "",
                    "meta_form_name": self.user_name,
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
