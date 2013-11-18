#!/usr/bin/python
# Copyright: 2013 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""
create a virtual environment and install moin2 (in development mode) and
its requirements.

needs: virtualenv, pip
"""

import MoinMoin  # validate python version
import argparse
import logging
import os.path
import subprocess
import sys
try:
    import virtualenv
except ImportError:
    sys.exit("""
Error: import virtualenv failed, either
  virtualenv is not installed (see installation docs)
or
  the virtual environment must be deactivated before rerunning quickinstall.py
""")


class QuickInstall(object):
    def __init__(self, source, venv=None):
        self.dir_source = source
        if not venv:
            base, source_name = os.path.split(source)
            venv = os.path.join(base, 'venv-{}-{}'.format(source_name, os.path.basename(sys.executable)))

        venv_home, venv_lib, venv_inc, venv_bin = virtualenv.path_locations(venv)
        self.dir_venv = venv_home
        self.dir_venv_bin = venv_bin

    def __call__(self):
        self.do_venv()
        self.do_install()
        self.do_catalog()

        sys.stdout.write("""
Succesfully created or updated venv
  {0}
You can run MoinMoin as
  {1}
""".format(self.dir_venv, os.path.join(self.dir_venv_bin, 'moin')))

    def do_venv(self):
        virtualenv.create_environment(self.dir_venv)

    def do_install(self):
        subprocess.check_call((
            os.path.join(self.dir_venv_bin, 'pip'),
            'install',
            # XXX: move cache to XDG cache dir
            '--download-cache',
            os.path.join(os.path.dirname(self.dir_venv), '.pip-download-cache'),
            '--editable',
            self.dir_source
        ))

    def do_catalog(self):
        subprocess.check_call((
            os.path.join(self.dir_venv_bin, 'python'),
            os.path.join(self.dir_source, 'setup.py'),
            'compile_catalog', '--statistics',
            # needed in case user runs quickinstall.py with a cwd other than the repo root
            '--directory', os.path.join(os.path.dirname(__file__), 'MoinMoin', 'translations'),
        ))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('venv', metavar='VENV', nargs='?', help='location of v(irtual)env')
    args = parser.parse_args()

    QuickInstall(os.path.dirname(os.path.realpath(sys.argv[0])), venv=args.venv)()
