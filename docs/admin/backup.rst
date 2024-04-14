==================
Backup and Restore
==================

Full Backup / Restore
=====================

The best way to recover from data loss is to have a **full** backup of your machine.
With this backup you can easily restore your machine to a working condition.

The procedure below explains how to selectively backup only the files
essential to your MoinMoin installation. While there is no need to maintain both a full
and a selective backup, having at least one of the two is strongly recommended.

Selective Backup
================
If you want a backup of MoinMoin and your data, then backup the following:

* your data, usually everything under wiki/
* moin configuration, e.g. wikiconfig.py
* logging configuration, e.g. logging.conf
* moin deployment script, e.g. moin.wsgi
* web server configuration, e.g. apache virtualhost config
* optional: moin code + dependencies; you should at least know which version
  you ran, so you can reinstall that version when you need to restore

To create a dump of all data stored in moinmoin (wiki items, user profiles), run the
following command::

 moin save --all-backends --file backup.moin

Please note that this file contains sensitive data like user profiles, wiki
contents, so store your backups in a safe place that no unauthorized
individual can access.

Backups require valid metadata to produce files which can be loaded
in particular, the size attribute must be correct for each revision.
if bad metadata is found during the backup,
there will be a warning logged and it is recommended
to run ``moin validate-metadata -a -f``
see :ref:`validate-metadata`

Selective Restore
=================

To restore all software and configuration files to their original
place, create an empty wiki first::

 moin index-create

To load the backup file into your empty wiki, run::

 moin load --file backup.moin

The index is removed and automatically recreated by the load command.
