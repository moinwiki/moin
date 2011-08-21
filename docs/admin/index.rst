====================
Working with indexes
====================
Configuration
=============
For correct script working you need ``index_dir`` and ``index_dir_tmp`` in
your wiki config. They have default values and most likely you don't want to change
them.

But if you want, try something like::

      index_dir = "/path/to/moin-2.0/wiki/index/"
      index_dir_tmp = "/path/to/moin-2.0/wiki/tmp_build/"

**Note:** Paths MUST BE absolute.

For using one index by multiple wikis (wiki farm) you must set up ``interwikiname``
parameter in your wiki config:

Example::

        interwikiname = u'MyWiki'

**Note:** For correct working interwikiname must be unique for each wiki.

Offline index manipulation
==========================
The main goal of offline index manipulation is to let wiki admin build, update, clean,
move and monitor state of indexes.

MoinMoin uses 2 indexes: ``latest-revs`` (index stores only current revisions)
and ``all-revs`` (index stores all revisions).

**Note:** If you see <indexname> below, use one of ``latest-revs``, ``all-revs``
or ``both`` 

Let's see what you can do with that stuff.

Build
-----
Just build fresh indexes using moin backend.

Example::

    moin index --for <indexname> --action build

Indexes will be built under ``index_dir_tmp`` so index building happens without
affecting the index your wiki engine uses currently.

Update
------
Update indexes to reflect the current backend contents. Add new stuff, remove
outdated stuff.

Example::

    moin index --for <indexname> --action update

Move
----
Moving indexes from ``index_dir_tmp`` to ``index_dir``.

Example::

    moin index --for <indexname> --action move

Clean
-----
Create empty index in ``index_dir`` for given index (previous will be erased).

Example::

    moin index --for <indexname> --action clean

Show
----
Showing content of index files in human readable form.

**Note:** field length limited to 40 chars.

**Note:** fields without attribute ``stored=True`` are not displayed.

Example::

    moin index --for indexname --action show

Building wiki farm
==================
Wiki farm allows admins create several wikis which share one index. So users
will be able to search in one wiki and also see results from others.

Before start you must prepair your wiki config.

For example, you have 3 wikis: ``Advertising``, ``Sales``, ``Engineering``

So, wiki configs will be looking like 

wikiconfig.py for ``Advertising``::

      index_dir = "/path/to/wiki/index/"
      index_dir_tmp = "/path/to/wiki/tmp_build/"
      interwikiname = u"Adverising"

wikiconfig.py for ``Sales``::

      index_dir = "/path/to/wiki/index/"
      index_dir_tmp = "/path/to/wiki/tmp_build/"
      interwikiname = u"Sales"

wikiconfig.py for ``Engineering``::

      index_dir = "/path/to/wiki/index/"
      index_dir_tmp = "/path/to/wiki/tmp_build/"
      interwikiname = u"Engineering"

So, after you defined configs you may start building indexes.

**Note:** Do not build indexes for two or more wikis in parallel, you'll damage
it or get traceback.

You must successively build index for each wiki in appropriate virtual env and then
move indexes from ``index_dir_tmp`` to ``index_dir``::

     moin index --for both --action build # in Advertising virtual env
     moin index --for both --action build # in Sales virtual env
     moin index --for both --action build # in Engineering virtual env
     moin index --for both --action move # you can run it from any virtual env

So, after that just run moin and try to search for something.
