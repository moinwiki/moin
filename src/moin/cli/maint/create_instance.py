# Copyright: 2020 MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create a MoinMoin wiki instance.

Activate a moin virtual env, then run this command:

    moin create-instance --path /path/to/new/instance

If path is not specified, the CWD is used as a default.

If the path does not exist, directories are created.
If wikiconfig.py does not exist, it is copied from the venv config directory.
If intermap.txt does not exist, it is copied from the venv contrib directory.
If a wiki_local directory does not exist, it is created.

Next: CD to new instance directory, run this command to initialize storage and index

    moin index-create -s -i

Optionally, populate the empty wiki with additional commands

    moin load-sample
    moin load <options>
    moin import19 <options>
    moin load-help <options>
"""

import os
import shutil

from flask_script import Command, Option

from moin import config
from moin import contrib

from moin import log
logging = log.getLogger(__name__)


class CreateInstance(Command):
    description = 'Create wikiconfig and wiki instance directories and copy required files.'

    option_list = [
        Option('--path', '-p', required=False, dest='path', type=str,
               help="Path to new wikiconfig dir, defaults to CWD if not specified."),
    ]

    def run(self, path):
        config_path = os.path.dirname(config.__file__)
        contrib_path = os.path.dirname(contrib.__file__)
        if not path:
            path = os.getcwd()
        if os.path.exists(path):
            print('Directory', os.path.abspath(path), 'already exists, using as wikiconfig dir.')
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
            shutil.copy(os.path.join(contrib_path, 'intermap.txt'), path)
        local_path = os.path.join(path, 'wiki_local')
        if not os.path.isdir(local_path):
            os.mkdir(local_path)
