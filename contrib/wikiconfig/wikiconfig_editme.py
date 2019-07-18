"""
Because MoinMoin 2 has no package releases yet, it can only be installed
using GIT clone, and updated with GIT pull. To use GIT pull, you must avoid
updating wikiconfig.py. You may override the wikiconfig.py default
configuration by uploading this file and wikiconfig_local.py to your wiki root.

The default wikiconfig.py has settings that are convenient for developers
but not appropriate for public wikis on the web. The default settings:
    * allow bots and users to edit and create items without logging in
    * allow bots and users to register new users with fake email addresses

The starting configuration below requires users to be logged in to edit items
and only superusers can register new users.

There are many other configuration options you may want to add here. See docs
and wikiconfig.py.
"""


from wikiconfig import *
from moin.storage import create_simple_mapping


class LocalConfig(Config):

    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data')

    # sitename is displayed in heading of all wiki pages
    sitename = 'My MoinMoin'

    # default root, use this to change the name of the default page
    # default_root = u'Home'  # FrontPage, Main, etc

    # options for new user registration
    registration_only_by_superuser = True  # if email configured, superuser can do > Admin > Register New User
    registration_hint = 'To request an account, see bottom of <a href="/Home">Home</a> page.'
    # to create a new user without configuring email, use the terminal/command/bash window
    # . activate  # windows: activate
    # moin account-create -n JaneDoe  -e j@jane.doe -p secretpasssword

    # allow user self-registration users with email verification; you must configure email to use this
    # user_email_verification = True  # less secure, web bots may create many unverified accounts with fake email addresses

    # to configure email, uncomment line below and choose (a) or (b)
    # mail_from = u"wiki <wiki@example.org>"  # the "from:" address [Unicode]
    # (a) using an SMTP server, e.g. "mail.provider.com" with optional `:port`appendix, which defaults to 25 (set None to disable mail)
    # mail_smarthost = "smtp.example.org"  # 'smtp.gmail.com:587'
    # mail_username = "smtp_username"
    # mail_password = "smtp_password"
    # (b) an alternative to SMTP may be the sendmail commandline tool:
    # mail_sendmail = "/usr/sbin/sendmail -t -i"

    # list of admin emails
    # admin_emails = ['me@mymain.com']
    # send tracebacks to admins
    # email_tracebacks = True

    # create a super user who will have access to administrative functions
    acl_functions = 'JaneDoe,JoeDoe:superuser'

    namespace_mapping, backend_mapping, acl_mapping = create_simple_mapping(
        uri='stores:fs:{0}/%(backend)s/%(kind)s'.format(data_dir),
        default_acl=dict(before='JaneDoe,JoeDoe:read,write,create,destroy,admin',
                         default='Known:read,write,create,destroy,admin All:read',
                         after='',
                         hierarchic=False, ),
        users_acl=dict(before='JaneDoe,JoeDoe:read,write,create,destroy,admin',
                       default='Known:read,write,create,destroy,admin All:read',
                       after='',
                       hierarchic=False, ),
        # userprofiles contain only metadata, no content will be created
        userprofiles_acl=dict(before='All:',
                              default='',
                              after='',
                              hierarchic=False, ),
    )


MOINCFG = LocalConfig
SECRET_KEY = 'you need to change this so it is really secret'
DEBUG = False
TESTING = False
