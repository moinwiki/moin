==================
Backup and Restore
==================

General remarks
===============

Everyone wants Restore. Nobody wants Backup.

.. warning::

   Above procedure doesn't work. Read below about a working procedure.

Full Backup / Restore
=====================

Of course it is the best to have a **full** backup of your machine. That way,
you can easily restore it to a working condition, even if things go severely
wrong.

If you have full backups, you maybe don't need the rather selective backup
procedure described below, because your full backup already includes everything
you need.

Selective Backup
================
If you just want a backup of moin and your data, backup these files:

* your data (most important)
* moin configuration (e.g. wikiconfig.py)
* logging configuration (e.g. logging.conf)
* moin script (e.g. moin.wsgi)
* web server configuration (e.g. apache virtualhost config)
* optional: moin code + dependencies (at least you should know which
  version you ran, so you can download and install that version when you
  need to restore)

To create a dump of all data stored in moin (wiki items, user profiles), do
this::

 moin save --file backup.moin

Please note that this file contains sensitive data (like user profiles, wiki
contents), so store your backups at a safe place and make sure no unauthorized
persons can access them.

Selective Restore
=================

Restore all software and configuration files (see above) to their original
place. Make sure your (empty) wiki works as expected::

 moin moin -s -i  # -s = create new storage
                  # -i = create new index

To load the backup file into your empty wiki, do this::

 moin load --file backup.moin

