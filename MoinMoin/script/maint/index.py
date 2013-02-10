# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - manage whoosh indexes (building, updating, (re)moving and displaying)
"""


from flask import current_app as app
from flask import g as flaskg
from flask.ext.script import Command, Option

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.constants.keys import LATEST_REVS, ALL_REVS


class IndexCreate(Command):
    description = 'Create empty indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        app.storage.create(tmp=tmp)


class IndexDestroy(Command):
    description = 'Destroy the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        app.storage.destroy(tmp=tmp)


class IndexBuild(Command):
    description = 'Build the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
        Option('--procs', '-p', required=False, dest='procs', type=int, default=1,
            help='Number of processors the writer will use.'),
        Option('--limitmb', '-l', required=False, dest='limitmb', type=int, default=10,
            help='Maximum memory (in megabytes) each index-writer will use for the indexing pool.'),
    ]

    def run(self, tmp, procs, limitmb):
        app.storage.rebuild(tmp=tmp, procs=procs, limitmb=limitmb)


class IndexUpdate(Command):
    description = 'Update the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        app.storage.update(tmp=tmp)


class IndexMove(Command):
    description = 'Move the indexes from the temporary to the normal location.'

    option_list = [
    ]

    def run(self):
        app.storage.move_index()


class IndexOptimize(Command):
    description = 'Optimize the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        app.storage.optimize_index(tmp=tmp)


class IndexDump(Command):
    description = 'Dump the indexes in readable form to stdout.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        for idx_name in [LATEST_REVS, ALL_REVS]:
            print " {0} {1} {2}".format("-" * 10, idx_name, "-" * 60)
            for kvs in app.storage.dump(tmp=tmp, idx_name=idx_name):
                for k, v in kvs:
                    print k, repr(v)[:70]
                print
