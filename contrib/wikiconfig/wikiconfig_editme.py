"""
Because MoinMoin 2 has no package releases yet, it can only be installed
using GIT clone, and updated with GIT pull. To use GIT pull, you must avoid
updating wikiconfig.py. You may override the wokiconfig.py default
configuration by uploading this file and wikiconfig_local.py to your wiki root.

The default wikiconfig.py has settings that are convenient for developers
but not appropriate for public wikis on the web. The default settings:
    * allow bots to edit and create items without logging in
    * allow bots to register new users with fake email addresses

The starting configuration below requires users to be logged in to edit items
and only superusers can register new users.

There are many other configuration options you may want to add here. See docs
and wikiconfig.py.
"""

from wikiconfig import *
from moin.constants.namespaces import NAMESPACE_DEFAULT, NAMESPACE_USERS

class LocalConfig(Config):

    # sitename is displayed in heading of all wiki pages
    sitename = u'My MoinMoin'

    # default root, use this to change the name of the default page
    # default_root = u'Home'  # FrontPage, Main, etc

    # options for new user registration
    registration_only_by_superuser = True  # if email configured, superuser can do > Admin > Register New User
    registration_hint = u'To request an account, see bottom of <a href="/Home">Home</a> page.'
    # to create a new user using the terminal window
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

    acls = {
        # maps namespace name -> acl configuration dict for that namespace
        NAMESPACE_DEFAULT: dict(before=u'JaneDoe,JoeDoe:read,write,create,destroy,admin',
                                default=u'Trusted:read,write,create,destroy,admin All:read',
                                after=u'',
                                hierarchic=False, ),
        NAMESPACE_USERS: dict(before=u'JaneDoe,JoeDoe:read,write,create,destroy,admin',
                                           default=u'Trusted:read,write,create,destroy,admin All:read',
                                           after=u'',
                                           hierarchic=False, ),
    }
    # namespace_mapping, backend_mapping, acl_mapping = create_mapping(uri, namespaces, backends, acls)

    # Uncomment this to override the default settings in wikiconfig.py
    # interwikiname = u'MyMoinMoin'  # use a stable and non-empty name
    # load the interwiki map from intermap.txt:
    # interwiki_map = InterWikiMap.from_file(os.path.join(wikiconfig_dir, 'contrib', 'interwiki', 'intermap.txt')).iwmap
    # we must add entries for 'Self' and our interwikiname
    # interwiki_map[interwikiname] = 'http://127.0.0.1:8080/'  # 'https://my.wiki.com'
    # interwiki_map['Self'] = 'http://127.0.0.1:8080/'


MOINCFG = LocalConfig
SECRET_KEY = 'you need to change this so it is really secret'
DEBUG = False
TESTING = False
