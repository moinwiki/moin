#!/usr/bin/python

import argparse
import logging
import os.path
import subprocess
import sys
import virtualenv


class QuickInstall(object):
    def __init__(self, source, venv=None):
        self.dir_source = source
        if not venv:
            base, source_name = os.path.split(source)
            venv = os.path.join(base, 'venv-{}-{}'.format(source_name, os.path.basename(sys.executable)))
        self.dir_venv = venv

    def __call__(self):
        self.do_venv()
        self.do_install()

        sys.stdout.write('''
Succesfully created or updated venv
  {0}
You can run MoinMoin as
  {0}/bin/moin
'''.format(self.dir_venv))

    def do_venv(self):
        virtualenv.create_environment(self.dir_venv)

    def do_install(self):
        subprocess.check_call((
            os.path.join(self.dir_venv, 'bin', 'pip'),
            'install',
            # XXX: move cache to XDG cache dir
            '--download-cache',
            os.path.join(os.path.dirname(self.dir_venv), '.pip-download-cache'),
            '--editable',
            self.dir_source
        ))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('venv', metavar='VENV', nargs='?', help='location of v(irtual)env')
    args = parser.parse_args()

    QuickInstall(os.path.dirname(os.path.realpath(sys.argv[0])), venv=args.venv)()
