"""
Copyright: 2019 MoinMoin:RogerHaase
License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

This Locust test script may be used to identify bugs that may occur
when an item is updated by multiple users in rapid succession.

This test requires user self-registration, set wikiconfig configuration to:
    registration_only_by_superuser = False
    user_email_verification = False
    edit_locking_policy = 'lock'
    edit_lock_time = 2  # or any number of minutes

Running this script will register users,
and each user will update the Home item multiple times. It is best to start with
an empty wiki (./m new-wiki).

To load test Moin2:
 * read about Locust at https://docs.locust.io/en/stable/index.html
 * install Locust per the docs
 * open a terminal window and start the built-in server (./m run)
   * (skip the above if using a remote server)
 * open a terminal window for the locus server
   * if Locust is installed in a virtualenv, activate it
   * cd to the directory where this file is located
   * start Locust, specify host (locust -f locustfile2.py --host=http://127.0.0.1:8080)
 * open a browser and direct it to http://127.0.0.1:8089
   * on Windows 10 you may have to use http://localhost:8089
   * start with 1 user with a hatch rate of 1 per second, increase users on subsequent tests
   * watch for error messages in both terminal windows and the browser
 * click the stop link on the browser to stop the test
 * check the contents of Home
   * success/fail messages should exist for each update attempt
      * fail messages for last update attempt may be missing
 * customize and repeat:
   * ./m del-wiki; ./m new-wiki
    * restart Moin2 buit-in server
    * restart Locust server
    * refresh browser window
"""


import sys
import argparse
import urllib
import urllib2
import datetime

from locust import HttpLocust, Locust, TaskSet, TaskSequence, task, seq_task


user_number = 0


def get_textarea(html):
    """Return contents of textarea where html is html output from +modify"""
    html = html.split('<textarea ')[1]
    html = html.split('>')[1]
    html = html.split('</textarea>')[0][:-10]
    return html


def format_date_time(dt=None):
    """Return current or passed (dt) time in a human readable format."""
    if dt is None:
        dt = datetime.datetime.now()
    fmt = '%Y-%m-%d %H:%M:%S'
    dt = dt.strftime(fmt)
    return dt


class UserSequence(TaskSequence):
    """
    Register a new user, login, modify the Home page several times, and logout.
    """

    @seq_task(0)
    def get_home(self):
        self.count = 0
        self.message = ''
        # Home and users/Home have been created by setup, see below
        response = self.client.get("/Home")
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(1)
    def click_login(self):
        global user_number
        user_number += 1
        self.user_name = 'JohnDoe' + str(user_number)
        self.user_email = self.user_name + '@john.doe'
        self.user_home_page = '/users/' + self.user_name
        print '==== starting user = %s ====' % self.user_name
        response = self.client.get("/+login")
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(2)
    def click_register(self):
        response = self.client.get("/+register")
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(3)
    def click_post_register(self):
        response = self.client.post("/+register",
                                    {"register_username": self.user_name,
                                     "register_password1": "locust123",
                                     "register_password2": "locust123",
                                     "register_email": self.user_email,
                                    })
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(4)
    def click_login_again(self):
        response = self.client.get("/+login")
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(5)
    def click_post_login(self):
        response = self.client.post("/+login",
                                    {"login_username": self.user_name,
                                     "login_password": "locust123",
                                     "login_submit": "1",
                                     "login_nexturl": "/Home",
                                    })
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(6)
    @task(10)
    def update_home_page(self):
        self.count += 1
        # click link to Home
        new_item_name = 'Home'
        response = self.client.get('/' + new_item_name)
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)
        # click modify link
        page_get = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default'
        response = self.client.get(page_get)
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)
        if 'is locked by' in response.content:
            # someone else has item locked for editing
            self.message += '\n\nItem %s is locked, %s cannot do change number %s' % (new_item_name, self.user_name, self.count)
            return
        textarea_data = get_textarea(response.content) + self.message
        self.message = ''
        dt = format_date_time()
        # complete form and post
        new_content = '%s\n\n%s update by Locust user %s at %s change number = %s\n\n' % (textarea_data, new_item_name, self.user_name, dt, self.count)
        new_page_post = '/+modify/' + new_item_name + '?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template='

        response = self.client.post(new_page_post,
                                    {"content_form_data_text": new_content,
                                     "comment": "my comment",
                                     "submit": "OK",
                                     'meta_form_contenttype': 'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "lime, orange",
                                     "meta_form_name": new_item_name,
                                     "extra_meta_text": '{"namespace": ""}',
                                     })
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)

    @seq_task(7)
    def logout(self):
        response = self.client.get(u"/+logout?logout_submit=1")
        if response.status_code != 200:
            print '%s: response.status_code = %s' % (sys._getframe().f_lineno, response.status_code)


class WebsiteUser(HttpLocust):

    task_set = UserSequence
    min_wait = 2000
    max_wait = 3000

    def setup(self):
        """create Home item"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--host', '-H')
        args, unknown = parser.parse_known_args()
        host = args.host
        if host:
            if host.endswith('/'):
                host = host[:-1]

            print '==== creating Home ===='
            url = host + u"/+modify/Home?contenttype=text%2Fx.moin.wiki%3Bcharset%3Dutf-8&itemtype=default&template="
            data = urllib.urlencode({"content_form_data_text": "= Home =\n * created by Locust",
                                     "comment": "",
                                     "submit": "OK",
                                     u'meta_form_contenttype': u'text/x.moin.wiki;charset=utf-8',
                                     "meta_form_itemtype": "default",
                                     "meta_form_acl": "None",
                                     "meta_form_tags": "None",
                                     "meta_form_name": "Home",
                                     "extra_meta_text": '{"namespace": "","rev_number": 1}',
                                     })
            content = urllib2.urlopen(url=url, data=data).read()
