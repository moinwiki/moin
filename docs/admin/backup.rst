==================
Backup and Restore
==================

General remarks
===============

Everyone wants Restore. Nobody wants Backup.

.. warning::

   Unfortunately, that doesn't work. Read below about a working procedure.

Full Backup / Restore
=====================

Of course, it's best to have a **full** backup of your machine. If you do,
you can easily restore it to a working condition, even if things go horribly wrong.

However, you can use the procedure below to selectively backup only the files
essential to your MoinMoin installation. While there is no need to maintain both a full
and a selective backup, having one of the two is strongly advised.

Selective Backup
================
If you just want a backup of MoinMoin and your data, backup the following files:

* your data (most important)
* moin configuration (e.g. wikiconfig.py)
* logging configuration (e.g. logging.conf)
* moin script (e.g. moin.wsgi)
* web server configuration (e.g. apache virtualhost config)
* optional: moin code + dependencies (you should at least know which
  version you ran, so you can download and install that version when you
  need to restore)

To create a dump of all data stored in moin (wiki items, user profiles), run the
following command::

 moin save --file backup.moin

Please note that this file contains sensitive data (like user profiles, wiki
contents), so store your backups in a safe place and make sure no unauthorized
individuals can access them.

Selective Restore
=================

To restore all software and configuration files (see above) to their original
place. Make sure your (empty) wiki works as expected::

 moin moin -s -i  # -s = create new storage
                  # -i = create new index

To load the backup file into your empty wiki, run::

 moin load --file backup.moin

