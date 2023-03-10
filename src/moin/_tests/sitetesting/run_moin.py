#!/usr/bin/env python

from flask_script import Manager, Server
import os
import shutil
from subprocess import run

from moin.app import create_app


def main():
    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(__file__))
        coms = [
                ['moin', 'index-create', '-s', '-i'],
                ['moin', 'load', '--file', '../../../../src/moin/contrib/sample-backup.moin'],
                ['moin', 'index-build'],
               ]
        for com in coms:
            run(com)
        manager = Manager(create_app)
        manager.add_command("moin", Server(host='127.0.0.1', port=9080))
        manager.run(default_command='moin')
    finally:
        shutil.rmtree('wiki')
        os.chdir(cwd)


if __name__ == '__main__':
    main()
