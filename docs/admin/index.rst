=======
Indexes
=======

General
=======
moin strongly relies on indexes that accelerate access to item metadata and data.
Indexes are used internally for many operations like item lookup, history,
iterating over items, search (also for interactive searches), etc..

So, you need to configure indexing correctly first.

moin will automatically update the index when items are created, updated, deleted,
destroyed or renamed (via the storage api of moin):
* when users change content via the user interface
* when xml is unserialized to load items into the backend

In case you have items changing without usage of the backend api or in case
your index gets damaged or lost, you need to manually do an index build -
or moin won't be able to work correctly.

Configuration
=============
Your wiki config needs ``index_dir`` and ``index_dir_tmp`` to point to different
directories. They have default values and most likely you don't need to change
them.

But if you want, try something like::

      index_dir = "/path/to/moin-2.0/wiki/index"
      index_dir_tmp = "/path/to/moin-2.0/wiki/tmp_build"

**Note:** Paths MUST BE absolute.


moin index script reference
===========================
You can use the ``moin index`` script to build, update, clean, move and monitor
indexes.

MoinMoin uses 2 indexes: ``latest-revs`` (index stores only current revisions)
and ``all-revs`` (index stores all revisions).

**Note:** If you see <indexname> below, use one of ``latest-revs``, ``all-revs``
or ``both`` 

Let's see what you can do with that stuff.

Build
-----
Index all revisions of all items to the index located in ``index_dir_tmp`` (we
use this separate location so that index building does not affect the index
your wiki engine is currently using).

If there is no index at that location yet, a new index will be built there.
If there is already an index at that location, that index will be extended.

Example::

    moin index --for <indexname> --action build

**Note:** moin won't use this index until you have moved it to ``index_dir``.

Move
----
Move indexes from ``index_dir_tmp`` to ``index_dir``.

Example::

    moin index --for <indexname> --action move

Update
------
Update the index located in ``index_dir`` to reflect the current backend
contents. Add new stuff, remove outdated stuff.

Example::

    moin index --for <indexname> --action update

Clean
-----
Create empty index in ``index_dir`` for given index (previous will be erased).

Example::

    moin index --for <indexname> --action clean

Show
----
Show contents of the index located in ``index_dir`` in human readable form.
This is mostly used for debugging.

Example::

    moin index --for indexname --action show

**Note:** field length limited to 40 chars.

**Note:** fields without attribute ``stored=True`` are not displayed.


Building an index for a single wiki
===================================
Build index at separate place, move it at right place:

     moin index --for both --action build
     moin index --for both --action move


Building an index for a wiki farm
=================================
If you run a wiki farm (multiple, but related wikis), you may share the index
between the farm wikis, so farm wiki users will be able to search in one wiki
and also see results from the others.

Before start you must prepare your wiki configs.

For example, imagine some company uses 2 farm wikis: ``Sales``, ``Engineering``

So, wiki configs will be looking like 

wiki config for ``Sales``::

      interwikiname = u"Sales"
      index_dir = "/path/to/wiki/index"
      index_dir_tmp = "/path/to/wiki/index_tmp"

wiki config for ``Engineering``::

      interwikiname = u"Engineering"
      index_dir = "/path/to/wiki/index"
      index_dir_tmp = "/path/to/wiki/index_tmp"

Now do the initial index building:

     moin index --for both --action build # in Sales virtual env
     moin index --for both --action build # in Engineering virtual env
     moin index --for both --action move # you can run it from any virtual env

Now you should have a shared index for all these wikis.

**Note:** Do not build indexes for multiple wikis in parallel, this is not
supported.

Building indexes while your wiki is running
===========================================
If you want to build an index while your wiki is running, you have to be
careful not to miss any changes that happen while you build the index.

``moin index --action build`` is made to not interfere with your running wiki.
So you can run this in parallel without taking your wiki offline.
Depending on the size of your wiki, index build can take rather long - but it
doesn't matter as you don't have to take your wiki offline for this.

But: if indexing takes rather long, it can easily happen that content that was
already put into the index is updated afterwards in the online wiki. So we need
to do a quick index update while the wiki is offline:

Offline your wiki (or at least make it read-only, so no data in it changes).

``moin index --action move`` to move indexes into place.

``moin index --action update`` to add anything we might have missed otherwise.
As this is not as much as doing a full index build, this should be rather quick
(but still: it has to look at every item in your wiki, whether it has been
updated after the initial index build).

Put your wiki back online again.

**Note:** Indexing puts load onto your server, so if you like to do regular
index rebuilds, schedule them at some time when your server is not too busy
otherwise.

