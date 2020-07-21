# Copyright: 2020 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - create a wiki instance
"""

import os
import shutil

from flask import current_app as app
from flask_script import Command, Option
from flask import g as flaskg

from moin import config

from moin import log
logging = log.getLogger(__name__)


class CreateInstance(Command):
    description = 'Create wiki instance directory and copy required files.'

    option_list = [
        Option('--path', '-p', required=True, dest='path', type=str,
            help="Path to wiki instance."),
    ]

    def run(self, path):
        config_path = os.path.dirname(config.__file__)
        if os.path.exists(path):
            print('Directory', os.path.abspath(path), 'already exists.')
        else:
            os.makedirs(path)
            print('Directory', os.path.abspath(path), 'created.')

        if os.path.isfile(os.path.join(path, 'wikiconfig.py')):
            print('wikiconfig.py already exists, not copied.')
        else:
            shutil.copy(os.path.join(config_path, 'wikiconfig.py'), path)

        if os.path.isfile(os.path.join(path, 'intermap.txt')):
            print('intermap.txt already exists, not copied.')
        else:
            shutil.copy(os.path.join(config_path, 'intermap.txt'), path)
