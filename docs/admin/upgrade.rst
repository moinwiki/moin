=========
Upgrading
=========

.. note::
   Internally, moin2 is very different than moin 1.x.

   moin 2.0 is *not* just a +0.1 step from 1.9 (like 1.8 -> 1.9), but the
   change of the major version number is indicating *major and incompatible changes*.

   So please consider it to be different and incompatible software that tries
   to be compatible in some areas:

   * Server and wiki engine Configuration: expect to review/rewrite it
   * Wiki content: expect 90% compatibility for existing moin 1.9 content.

     * The most commonly used simple moin wiki markup (like headlines, lists, bold) has not changed
     * CamelCase auto links will be converted to explicit [[CamelCase]] links
     * [[attachment:my.jpg]] will be converted to [[/my.jpg]]
     * {{attachment:my.jpg}} will be converted to {{/my.jpg}}
     * expect to change custom macros, parsers, action links, 3rd party extensions

From moin < 1.9
===============
If you run an older moin version than 1.9, please first upgrade to a recent
moin 1.9.x version (preferably >= 1.9.7) before upgrading to moin2.
You may want to run that for a while to be sure everything is working as expected.

Note: Both moin 1.9.x and moin2 are WSGI applications.
Upgrading to 1.9 first also makes sense concerning the WSGI / server side.


From moin 1.9.x
===============

If you want to keep your user's password hashes and migrate them to moin2,
make sure you use moin >= 1.9.7 WITH enabled passlib support and that all
password hashes stored in user profiles are {PASSLIB} hashes. Other hashes
will get removed in the migration process and users will need to do password
recovery via email (or with admin help, if that does not work).


Backup
------
Have a backup of everything, so you can go back in case it doesn't do what
you expect. If you have a testing machine, it is a good idea to try it there
first and not directly modify your production machine.


Install moin2
-------------
Install and configure moin2, make it work, and start configuring it from
the moin2 sample config. Do *not* just use your 1.9 wikiconfig.


Adjusting the moin2 configuration
---------------------------------
It is essential that you edit wikiconfig.py before you import your 1.9
data. In particular, review the settings for::

- sitename
- interwikiname
- SECRET_KEY
- secrets
- default_acl
- users_acl


Clean up your moin 1.9 data
---------------------------
It is a good idea to clean up your 1.9 data first, before trying to import
it into moin2. In doing so you can avoid quite some
warnings that the moin2 importer would produce.

You do this with moin *1.9*, using these commands::

  moin ... maint cleanpage
  moin ... maint cleancache

Deleted pages will not be migrated. A message will be written to the
log for each deleted page.


Importing your moin 1.9 data
----------------------------
Before importing your existing wiki data please ensure you have created an instance
and index as described in the install section above using commands::

  moin create-instance
  moin index-create

The import19 cli subcommand will read your 1.9 data_dir (pages, attachments and users),
convert the data, write it to your moin2 storage and build the index::

  moin import19 --data_dir /<path to moin1.9>/wiki/data

Please review the logfile to find out whether the importer had critical issues with your data.

By default, all items using moin 1.9 markup are converted to moin 2 markup. The converted
revision will have a timestamp one second later than the last revision's timestamp to preserve
revision history.

Page revisions that were created with leading `#format creole` and `#format rst` commands
will retain the creole and rst markups.

There is an additional option to convert pages with moin wiki markup using one of the other moin2
output converters: markdown, rst, html, or docbook.
Add the `--markup_out` or `-m` option to the `moin import19` command above. To
convert the last revision of all pages with moin wiki markup to markdown::

 -m markdown

The import19 process will create a wiki directory structure different from moin 1.9.
There will be three namespaces under /wiki/data: "default", "userprofiles", and "users".
Each namespace will have "data" and "meta" subdirectories. Additional custom namespaces can
be created by editing wikiconfig.py.

Most of the data from the 1.9 pages directory will be converted to the "default" directory. User
home pages and subpages will be converted to the "users" directory. The data from the 1.9 "users"
directory will be converted to the "userprofiles" directory. The "userprofiles" directory
contains data used internally and should always be protected from any access by ACLs.

If you are importing a large wiki with more than 1000 entries or revisions, the index building
part of the import will be time-consuming. You can use the following options to speed up the process::

 --procs <number of processors> --limitmb <memory in mb for each process>

Choose the values according to your available hardware resources. The defaults are 1 process and 256 mb memory.
See the `Whoosh Tips for speeding up batch indexing docs <https://whoosh.readthedocs.io/en/latest/batch.html>`_ for details.

Testing
-------
Review the logs for error messages. Start the moin server and try the "Index" and "History"
views to see what is included. Check whether your data is complete and rendering correctly.

If you find issues with data migration from moin 1.9 to 2, please check the
moin2 issue tracker.


Keep your backups
-----------------
Make sure you keep all backups of your moin 1.9 installation, such as code, config,
data, just in case you are not happy with moin2 and need to revert to the old version.


Converting after reverting
--------------------------
.. if the above title is changed, also change CONTENTTYPES_HELP_DOCS in constants/contenttypes.py

The import19 process converts text items using Moinmoin 1.9 syntax to
Moinmoin 2.0 syntax.

The conversion is accomplished by creating a new revision of each moin wiki text item.
Click the History link under the Item Views panel to view the revisions.
The latest revision will have a content type of "Moinmoin" while the older revisions
created prior to conversion will have a content type of "Moinmoin 1.9"
Click the Diff link to see the content changes made by import19.

If a moin wiki item is reverted to a revision having a content type of "Moinmoin 1.9"
with embedded old style CamelCase auto links and/or attachments (`{{attachment:my.jpg}}`),
the revision is not converted to the Moinmoin 2 syntax automatically. Editors must do
the conversion by clicking the Convert link within the Item Views panel.

Reverted revisions left in the Moinmoin 1.9 format will render correctly and
the reverted item may be updated and saved using the old 1.9 syntax. However,
it is recommended that all such revisions be converted to the new moin syntax
because the old CamelCase and attachment conventions are deprecated and will
never be included in the moin 2 docs.
