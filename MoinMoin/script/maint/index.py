# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - manage whoosh indexes (building, updating, (re)moving and displaying)
"""


from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin import log
logging = log.getLogger(__name__)


class IndexCreate(Command):
    description = 'Create empty indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.create(tmp=tmp)


class IndexDestroy(Command):
    description = 'Destroy the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.destroy(tmp=tmp)


class IndexBuild(Command):
    description = 'Build the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
        Option('--procs', '-p', required=False, dest='procs', type=int, default=None,
            help='Number of processors the writer will use.'),
        Option('--limitmb', '-l', required=False, dest='limitmb', type=int, default=10,
            help='Maximum memory (in megabytes) each index-writer will use for the indexing pool.'),
    ]

    def run(self, tmp, procs, limitmb):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.rebuild(tmp=tmp, procs=procs, limitmb=limitmb)


class IndexUpdate(Command):
    description = 'Update the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.update(tmp=tmp)


class IndexMove(Command):
    description = 'Move the indexes from the temporary to the normal location.'

    option_list = [
    ]

    def run(self):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.move_index()


class IndexOptimize(Command):
    description = 'Optimize the indexes.'

    option_list = [
        Option('--tmp', action="store_true", required=False, dest='tmp', default=False,
            help='use the temporary location.'),
    ]

    def run(self, tmp):
        unprotected_storage = flaskg.unprotected_storage = app.unprotected_storage
        unprotected_storage.optimize_index(tmp=tmp)

