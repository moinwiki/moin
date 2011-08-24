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


Adjusting the moin2 configuration
---------------------------------
It is essential that you adjust the wiki config before you export your 1.9
data to xml:

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

    # think about which backend you will use in the end and configure
    # it here (this is NOT the fs19 backend!):
    namespace_mapping = \
        create_simple_mapping(
            backend_uri='fs2:/some/path/%%(nsname)s',
            content_acl=dict(before=u'', # acl_rights_before in 1.9
                             default=u'', # acl_rights_default
                             after=u'', # acl_rights_after
                             hierarchic=False), # acl_hierarchic
            user_profile_acl=dict(before=u'',
                                  default=u'',
                                  after=u'',
                                  hierarchic=False),
        )

Exporting your moin 1.9 data to an XML file
-------------------------------------------
moin2 can use the `fs19` storage backend to access your moin 1.9 content
(pages, attachments and users). The fs19 backend is a bit more than just
a backend - it also makes the moin 1.9 data look like moin2 data when
moin accesses them. To support this, it is essential that you adjust your
wiki config first, see previous section.

Then, use a **copy** of your 1.9 content, do not point moin2 it at your
original data::

    moin maint_xml --moin19data=/your/moin19/data --save --file=moin19.xml

This will serialize all your moin 1.9 data into moin19.xml.

Note: depending on the size of your wiki, this can take rather long and consume
about the same amount of additional disk space.

Importing the XML file into moin2
---------------------------------
Just load moin19.xml into the storage backend you have already configured::

    moin maint_xml --load --file=moin19.xml

Note: depending on the size of your wiki, this can take rather long and consume
about the same amount of additional disk space.

Testing
-------
Just start moin now, it should have your data now.

Try "Index" and "History" views to see what's in there.

Check whether your data is complete and working OK.

If you find issues with data migration from moin 1.9 to 2, please check the
moin2 issue tracker.

Cleanup
-------
If you made a **copy** of your 1.9 content, you can remove that copy now.

Maybe keep the moin19.xml for a while in case you want to try other backends,
but later you can delete that file.

Make sure you keep all backups of your moin 1.9 installation (code, config,
data), just for the case you are not happy with moin2 and need to go back for
some reason.

