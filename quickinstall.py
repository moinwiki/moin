#!/usr/bin/python
# Copyright: 2013 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""
Create a virtual environment and install moin2 (in development mode) and
its requirements.

needs: virtualenv, pip
"""


import argparse
import logging
import os
import subprocess
import sys
import platform
try:
    import virtualenv
except ImportError:
    sys.exit("""
Error: import virtualenv failed, either virtualenv is not installed (see installation docs)
or the virtual environment must be deactivated before rerunning quickinstall.py
""")

from make import Commands, WINDOWS_OS, M, ACTIVATE


if sys.hexversion < 0x2070000 or sys.hexversion > 0x2999999:
    sys.exit("Error: MoinMoin requires Python 2.7.x., current version is %s\n" % (platform.python_version(), ))


WIN_INFO = 'm.bat, activate.bat, and deactivate.bat are created by quickinstall.py'
NIX_INFO = 'the m bash script and the activate symlink are created by quickinstall.py'


def create_m():
    """Create an 'm.bat or 'm' bash script that will run make.py using this Python"""
    if WINDOWS_OS:
        with open('m.bat', 'w') as f:
            f.write(':: {0}\n\n@{1} make.py %*\n'.format(WIN_INFO, sys.executable))
    else:
        with open('m', 'w') as f:
            f.write('# {0}\n\n{1} make.py $*\n'.format(NIX_INFO, sys.executable))
            os.fchmod(f.fileno(), 0775)


class QuickInstall(object):
    def __init__(self, source, venv=None, download_cache=None):
        self.dir_source = source
        if venv is None:
            base, source_name = os.path.split(source)
            executable = os.path.basename(sys.executable).split('.exe')[0]
            venv = os.path.join(base, '{0}-venv-{1}'.format(source_name, executable))
        if download_cache is None:
            # make cache sibling of ~/pip/pip.log or ~/.pip/pip.log
            if WINDOWS_OS:
                download_cache = '~/pip/pip-download-cache'
            else:
                # XXX: move cache to XDG cache dir
                download_cache = '~/.pip/pip-download-cache'

        venv = os.path.abspath(venv)
        venv_home, venv_lib, venv_inc, venv_bin = virtualenv.path_locations(venv)
        self.dir_venv = venv_home
        self.dir_venv_bin = venv_bin
        self.download_cache = os.path.normpath(os.path.expanduser(download_cache))

    def __call__(self):
        self.do_venv()
        self.do_helpers()
        self.do_install()
        self.do_catalog()

        sys.stdout.write("""

Successfully created or updated venv at {0}
""".format(self.dir_venv))

    def do_venv(self):
        virtualenv.create_environment(self.dir_venv)

    def get_pip_version(self):
        """Return pip version as a list: [1, 5, 1]"""
        command = ACTIVATE + 'pip --version'
        pip_txt = subprocess.check_output(command, shell=True)
        # expecting pip_txt similar to "pip 1.4.1 from /bitbucket/moin-2.0..."
        pip_txt = pip_txt.split()
        if pip_txt[0] == 'pip':
            pip_version = [int(x) for x in pip_txt[1].split('.')]
            return pip_version
        else:
            sys.exit("Error: 'pip --version' produced unexpected results: '{0}".format(' '.join(pip_txt)))

    def do_install(self):
        pip_version = self.get_pip_version()
        args = [
            os.path.join(self.dir_venv_bin, 'pip'),
            'install',
            '--upgrade',
            '--editable',
            self.dir_source,
        ]
        if pip_version < [6, 0]:
            args += ['--download-cache', self.download_cache, ]
        if pip_version >= [1, 5]:
            args += ['--process-dependency-links', ]
        if pip_version >= [9, 0]:
            args += ['--upgrade-strategy=eager', ]
        subprocess.check_call(args)

    def do_catalog(self):
        subprocess.check_call((
            os.path.join(self.dir_venv_bin, 'python'),
            os.path.join(self.dir_source, 'setup.py'),
            'compile_catalog', '--statistics',
            # needed in case user runs quickinstall.py with a cwd other than the repo root
            '--directory', os.path.join(os.path.dirname(__file__), 'src', 'moin', 'translations'),
        ))

    def create_wrapper(self, filename, target):
        """Create files in the repo root that wrap files in <path-to-virtual-env>\Scripts."""
        target = os.path.join(self.dir_venv_bin, target)
        with open(filename, 'w') as f:
            f.write(':: {0}\n\n@call {1} %*\n'.format(WIN_INFO, target))

    def do_helpers(self):
        """Create small helper scripts or symlinks in repo root, avoid keying the long path to virtual env."""
        create_m()  # recreate m.bat or ./m to insure it is consistent with activate
        if WINDOWS_OS:
            # windows commands are: activate | deactivate
            self.create_wrapper('activate.bat', 'activate.bat')
            self.create_wrapper('deactivate.bat', 'deactivate.bat')
        else:
            # linux commands are: source activate | deactivate
            if os.path.exists('activate'):
                os.unlink('activate')
            os.symlink(os.path.join(self.dir_venv_bin, 'activate'), 'activate')  # no need to define deactivate on unix


if __name__ == '__main__':
    if os.path.isfile('m') or os.path.isfile('m.bat'):
        # create the virtual env directory and fill it with moin2 requirements
        logging.basicConfig(level=logging.INFO)
        parser = argparse.ArgumentParser()
        parser.add_argument('venv', metavar='VENV', nargs='?', help='location of v(irtual)env')
        parser.add_argument('--download-cache', dest='download_cache', help='location of pip download cache')
        args = parser.parse_args()
        QuickInstall(os.path.dirname(os.path.realpath(sys.argv[0])), venv=args.venv, download_cache=args.download_cache)()
    else:
        # user is running "python quickinstall.py" after fresh clone
        create_m()  # create "m" or "m.bat" file so above IF will be true next time around
        # run the cmd_quickinstall code in make.py so user will see a few success/failure messages instead of ~500 info messages
        commands = Commands()
        command = getattr(commands, 'cmd_quickinstall')
        # run this same script (quickinstall.py) again in a subprocess to create the virtual env
        command(*sys.argv[1:])  # pass args user may have entered: <override-path-to-venv> --download_cache <override-path-to-cache>
        # a few success/failure messages will have printed on users terminal, suggest next step
        print '\n> > > Type "%s" for menu < < <' % M
