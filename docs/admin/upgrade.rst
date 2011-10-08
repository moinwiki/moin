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
It is essential that you adjust the wiki config before you import your 1.9
data:

Configuration::

    from os.path import join
    from MoinMoin.storage import create_simple_mapping

    interwikiname = u'...' # critical, make sure it is same as in 1.9!
    sitename = u'...' # same as in 1.9
    item_root = u'...' # see page_front_page in 1.9

    # configure backend and ACLs to use in future
    # TODO


Clean up your moin 1.9 data
---------------------------
It is a good idea to clean up your 1.9 data first, before trying to import
it into moin2. By getting the data into good shape you can avoid quite some
warnings the importer would emit otherwise.

You do this with moin 1.9 (!), using these commands::

  moin ... maint cleanpage
  moin ... maint cleancache

.. todo::
   add more infos about handling of deleted pages


Importing your moin 1.9 data
----------------------------
It is assumed that you have no moin2 storage and no index created yet,
thus we include -s and -i options to create the storage and an empty index.

The import19 will then read your 1.9 data_dir (pages, attachments and users),
convert the data as needed and write it to your moin2 storage (and also
build the index)::

  moin import19 -s -i --data_dir /your/moin/1.9/data 1>import1.log 2>import2.log

If you use the command as given, it will write all output into 2 log files,
please review them to find whether the importer had critical issues with your
data.


Testing
-------
Just start moin now, it should have your data now.

Try "Index" and "History" views to see what's in there.

Check whether your data is complete and working OK.

If you find issues with data migration from moin 1.9 to 2, please check the
moin2 issue tracker.


Keep your backups
-----------------
Make sure you keep all backups of your moin 1.9 installation (code, config,
data), just for the case you are not happy with moin2 and need to go back for
some reason.

