====================
Working with indexes
====================
Requirements
============
For correct script working you should set ``index_dir`` and ``index_dir_tmp`` values in
your local config.

For example ``wikiconfig_editme.py``::

   from wikiconfig import *

   class LocalConfig(Config):
      index_dir = "/home/marchael/Downloads/moin/moin2/moin-2.0/wiki/index/"
      index_dir_tmp = "/home/marchael/Downloads/moin/moin2/moin-2.0/wiki/tmp_build/"

   MOINCFG = LocalConfig

**Note:** Paths MUST BE absolute

Rebuiling indexes at runtime
============================
For large wiki(s) rebuilding indexes may take several hours
and all this time wiki will be unreachable for using.

But you may use following sequence for building indexes while moin is working:
 * Build indexes in another directory
 * Stop moin
 * Replace currently used index directory by the new index directory
 * Update indexes if needed
 * Run moin

You may use following commands in virtual env::

   moin rebuild_indexes --for both --action build # build indexes in tmp dir
   # stop wiki
   moin rebuild_indexes --for both --action move  # move indexes tmp dir to 
                                                  # current index directory
   moin update_indexes                            # update indexes
   # start wiki

**Note:** If you don't want to rebuild both indexes you could also try
``--for all-revs`` or ``--for latest-revs``.


For cleaning both indexes in base directory you may try::

   moin --for both --action clean


