"""
MoinMoin - build xapian search engine's index

@copyright: 2006-2009 MoinMoin:ThomasWaldmann
@license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import os
import errno
import shutil

from MoinMoin.script import MoinScript

class IndexScript(MoinScript):
    """\
Purpose:
========
This tool allows you to control xapian's index of Moin.

Detailed Instructions:
======================
General syntax: moin [options] index build [build-options]

[options] usually should be:
    --config-dir=/path/to/my/cfg/ --wiki-url=http://wiki.example.org/

[build-options] see below:
    Please note:
    * You must run this script as the owner of the wiki files,
      usually this is the web server user.
    * You may add the build-option --files=files.lst to let the indexer
      also consider the filesystem filenames contained in that file (one
      filename per line). Search results from these files will be "found"
      under a special pseudo page called FS (like File System).
      Without this option, the indexer will just consider wiki items.

    1. Conditionally (considering modification time) update the index:
       moin ... index build --mode=update

    2. Unconditionally add to the index:
       moin ... index build --mode=add

    3. Completely rebuild the index (1-stage):
       moin ... index build --mode=rebuild

       Note: until it has completely built the new index, the wiki will still
       use the old index. After rebuild has completed, it kills the old index
       and moves the new index into its place.
       If the wiki uses the index at that moment, that might have unwanted side
       effects. If you want to avoid that and you can accept a short downtime,
       consider using this safer method:

       Completely rebuild the index (2-stage):
       # takes long, does not interfere with wiki searches:
       moin ... index build --mode=buildnewindex
       stop this moin wiki process(es)
       # quick, replaces the old index with the new one:
       moin ... index build --mode=usenewindex
       start this moin wiki process(es)
"""

    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "--files", metavar="FILES", dest="file_list",
            help="filename of file list, e.g. files.lst (one file per line)"
        )
        self.parser.add_option(
            "--mode", metavar="MODE", dest="mode",
            help="either add (unconditionally add), update (conditional update), rebuild (complete 1-stage index rebuild)"
                 " or buildnewindex and usenewindex (complete 2-stage index rebuild)"
        )

    def mainloop(self):
        self.init_request()
        # Do we have additional files to index?
        if self.options.file_list:
            self.files = file(self.options.file_list)
        else:
            self.files = None
        self.command()

class PluginScript(IndexScript):
    """ Xapian index build script class """

    def command(self):
        from MoinMoin.search.Xapian import XapianIndex
        mode = self.options.mode
        if mode in ('rebuild', 'buildnewindex'):
            # rebuilding the DB into a new index directory, so the rebuild
            # process does not interfere with the currently in-use DB
            idx_mode, idx_name = 'add', 'index.new'
        elif mode in ('add', 'update'):
            # update/add in-place
            idx_mode, idx_name = mode, 'index'
        elif mode == 'usenewindex':
            pass # nothing todo
        else:
            pass # XXX give error msg about invalid mode

        if mode != 'usenewindex':
            idx = XapianIndex(self.request, name=idx_name)
            idx.indexPages(self.files, idx_mode)

        if mode in ('rebuild', 'usenewindex'):
            # 'rebuild' is still a bit dirty, because just killing old index will
            # fail currently running searches. Thus, maybe do this in a time
            # with litte wiki activity or better use 'buildnewindex' and
            # 'usenewindex' (see above).
            # XXX code here assumes that idx.db is a directory
            # TODO improve this with xapian stub DBs
            idx_old = XapianIndex(self.request, name='index').db
            idx_new = XapianIndex(self.request, name='index.new').db
            try:
                shutil.rmtree(idx_old)
            except OSError, err:
                if err.errno != errno.ENOENT: # ignore it if we have no current index
                    raise
            os.rename(idx_new, idx_old)

