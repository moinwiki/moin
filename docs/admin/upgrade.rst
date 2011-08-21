=========
Upgrading
=========

.. note::
   moin2 is internally working very differently compared to moin 1.x.

   moin 2.0 is *not* just a +0.1 step from 1.9 (like 1.8 -> 1.9), but the
   change of the major revision is indicating *major and incompatible changes*.

   So please consider it to be a different, incompatible software that tries
   to be compatible at some places:

   * Server and wiki engine Configuration: expect to review/rewrite it
   * Wiki content: expect 90% compatibility for existing moin 1.9 content. The
     most commonly used simple moin wiki markup (like headlines, lists, bold,
     ...) will still work, but expect to change macros, parsers, action links,
     3rd party extensions (for example).

From moin < 1.9
===============
As MoinMoin 1.9.x has been out there for quite a while, we only describe how
to upgrade from moin 1.9.x to moin2. If you still run an older moin
version than this, please first upgrade to moin 1.9.x. Maybe run 1.9.x for a
while, so you can be sure everything is working as expected.

Note: moin 1.9.x is a WSGI application, moin2 is also a WSGI application.
So, upgrading to 1.9 first makes also sense concerning the WSGI / server side.


From moin 1.9.x
===============
Backup
------
Have a backup of everything, so you can go back in case it doesn't do what
you expect. If you have a 2nd machine, it is a good idea to try it there
first (and not directly modify your production machine).


Install moin2
-------------
Install and roughly configure moin2, make it work, start configuring it from
the moin2 sample config (do not just use your 1.9 wikiconfig).


Configure moin2 to read moin 1.9 data
-------------------------------------
moin2 can use the `fs19` storage backend to access your moin 1.9 content
(pages, attachments and users).

Use a **copy** of the 1.9 content, do not point it at your original data.

Configuration::

    from os.path import join
    from MoinMoin.storage.backends import create_simple_mapping

    interwikiname = ... # critical, make sure it is same as in 1.9!
    sitename = ... # same as in 1.9
    item_root = ... # see page_front_page in 1.9
    theme_default = ... # (only supported value is "modernized")
    language_default = ...
    mail_smarthost = ...
    mail_sendmail = ...
    mail_from = ...
    mail_login = ...
    # XXX default_markup must be 'wiki' right now
    page_category_regex = ... # XXX check
    data_dir = ... # same as in 1.9, user profiles must be in data_dir/user
    namespace_mapping = \
        create_simple_mapping(
            backend_uri='fs19:%s' % data_dir,
            content_acl=dict(before=u'', # acl_rights_before in 1.9
                             default=u'', # acl_rights_default
                             after=u'', # acl_rights_after
                             hierarchic=False), # acl_hierarchic
            user_profile_acl=dict(before=u'',
                                  default=u'',
                                  after=u'',
                                  hierarchic=False),
        )

    save_xml = '.../backup.xml'
    load_xml = None

If you start moin now, it will serialize everything it finds in its backend
to an xml file.

Keep the xml file (you can use it to try different backend configurations).


Writing the data to a moin2 backend
-----------------------------------
Reconfigure moin2 to use the backend you like to use (e.g. fs2 backend)::

    # use same as you already have, but:
    backend_uri='fs2:/some/path/%%(nsname)s',

    save_xml = None
    load_xml = '.../backup.xml'

If you start moin2 now, it will unserialize your xml file to fill the
backend with your data.


Cleaning up the configuration
-----------------------------
You need to import the xml only once, so after doing that, clean up your config::

    save_xml = None
    load_xml = None

