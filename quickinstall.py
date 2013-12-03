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
import os
import subprocess
import sys
try:
    import virtualenv
except ImportError:
    sys.exit("""
Error: import virtualenv failed, either virtualenv is not installed (see installation docs)
or the virtual environment must be deactivated before rerunning quickinstall.py
""")


class QuickInstall(object):
    def __init__(self, source, venv=None, download_cache=None):
        self.dir_source = source
        if venv is None:
            base, source_name = os.path.split(source)
            venv = os.path.join(base, '{}-venv'.format(source_name))
        if download_cache is None:
            # make cache sibling of ~/pip/pip.log or ~/.pip/pip.log
            if os.name == 'nt':
                download_cache = '~/pip/pip-download-cache'
            else:
                # XXX: move cache to XDG cache dir
                download_cache = '~/.pip/pip-download-cache'

        venv_home, venv_lib, venv_inc, venv_bin = virtualenv.path_locations(venv)
        self.dir_venv = venv_home
        self.dir_venv_bin = venv_bin
        self.download_cache = os.path.normpath(os.path.expanduser(download_cache))

    def __call__(self):
        self.do_venv()
        self.do_install()
        self.do_catalog()
        self.do_helpers()

        sys.stdout.write("""
Pip cache location is at {0}

Successfully created or updated venv at {1}
""".format(self.download_cache, self.dir_venv))

    def do_venv(self):
        virtualenv.create_environment(self.dir_venv)

    def do_install(self):
        subprocess.check_call((
            os.path.join(self.dir_venv_bin, 'pip'),
            'install',
            '--download-cache',
            self.download_cache,
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

    def do_helpers(self):
        """Create small helper scripts or symlinks in repo root."""

        def create_wrapper(filename, contents):
            """Create files in the repo root that wrap files in the v-env/bin or v-env\Scripts."""
            with open(filename, 'w') as f:
                f.write(contents)

        if os.name == 'nt':
            # windows commands are: activate | deactivate | moin
            create_wrapper('activate.bat', '@call {}\n'.format(os.path.join(self.dir_venv_bin, 'activate.bat')))
            create_wrapper('deactivate.bat', '@call {}\n'.format(os.path.join(self.dir_venv_bin, 'deactivate.bat')))
            create_wrapper('moin.bat', '@call {} %*\n'.format(os.path.join(self.dir_venv_bin, 'moin.exe')))
        else:
            # linux commands are: source activate | deactivate | ./moin
            if os.path.exists('activate'):
                os.unlink('activate')
            if os.path.exists('moin'):
                os.unlink('moin')
            os.symlink(os.path.join(self.dir_venv_bin, 'activate'), 'activate')  # no need to define deactivate on unix
            os.symlink(os.path.join(self.dir_venv_bin, 'moin'), 'moin')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('venv', metavar='VENV', nargs='?', help='location of v(irtual)env')
    parser.add_argument('--download_cache', dest='download_cache', help='location of pip download cache')
    args = parser.parse_args()

    QuickInstall(os.path.dirname(os.path.realpath(sys.argv[0])), venv=args.venv, download_cache=args.download_cache)()
