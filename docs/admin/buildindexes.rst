====================
Working with indexes
====================
Requirements
============
For correct script working you should set ``index_dir`` and ``index_dir_tmp`` values in
your wiki config.

For example::

      index_dir = "/home/marchael/moin-2.0/wiki/index/"
      index_dir_tmp = "/home/marchael/moin-2.0/wiki/tmp_build/"

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

   moin index --for both --action build   # build indexes in index_dir_tmp
   # TODO: insert a command here to stop your moin
   moin index --for both --action update  # update indexes
   moin index --for both --action move    # move indexes index_dir_tmp to 
                                          # current index_dir
   # TODO: insert a command here to start your moin

**Note:** If you don't want to rebuild\update both indexes you can use
``--for all-revs`` or ``--for latest-revs``.


For cleaning both indexes in ``index_dir`` you may try::

   moin index --for both --action clean


